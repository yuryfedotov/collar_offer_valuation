from django.shortcuts import render
from bokeh.plotting import figure
from bokeh.layouts import gridplot
from bokeh.embed import components
from bokeh.models import Span, BoxAnnotation, LinearAxis, Range1d
from bokeh.palettes import Paired12
import numpy as np

def index(request):
    return render(request, 'index.html')

def dashboard(request):
    
    # 1.1. Getting inputs

    bidder_name = str(request.POST.get("bidderName"))
    target_name = str(request.POST.get("targetName"))
    collar_type = str(request.POST.get("collarType"))

    NB0 = int(request.POST.get("bidderSharesBefore")) # Bidder shares before the deal
    NT0 = int(request.POST.get("targetSharesBefore")) # Target shares before the deal

    SB0 = float(request.POST.get("bidderPriceBefore")) # Bidder price 1 day prior to announcement
    ST0 = float(request.POST.get("targetPriceBefore")) # Target price 1 day prior to announcement
    RetB = float(request.POST.get("bidderDailyReturn")) # Daily return of bidder during the bid period
    StdB = float(request.POST.get("bidderDailyStd")) # Daily std of bidder's return during the bid period
    DP = float(request.POST.get("desiredPremium")) # Minimum premium desired by target, to the pre-announcement price
    RP = float(request.POST.get("readyPremium")) # Maximum premium bidder is ready to pay, to the pre-announcement price

    simulations = 100000 # Number of simulations in the model
    T = int(request.POST.get("daysBetween")) # Days between merger agreement and deal closing
    dt = 1 # Always 1, as we use daily intervals
    GBMsteps = round(T/dt) # Number of discrete intervals of GBM
    avgper = int(request.POST.get("avgPer")) # Averaging period, according to collar agreement

    # 1.2. Modelling bidder's effective price
    
    SBTeff_list = []

    for x in range(simulations):

        t = np.linspace(0, T, GBMsteps)
        N = np.random.standard_normal(size = GBMsteps)
        R = (t != 0) * (RetB * dt * t + StdB * np.cumsum(N) * np.sqrt(dt))
        SB_path = SB0 * (1 + R)
        SBTeff = np.mean(SB_path[-avgper:])
        SBTeff_list.append(SBTeff)

    SBTeff_array = np.sort(np.array(SBTeff_list)) # This is the SM output: array of effective bidder's stock prices    
    SBTeff_mean = np.mean(SBTeff_array)
    SBTeff_std = np.std(SBTeff_array)

    # SECTION 2. A DEAL WITHOUT A COLLAR

    # 2.1. Required assumptions
    BaseER = float(request.POST.get("baseER"))

    # 2.2. Back-end calculations
    NocPTT = SBTeff_array * BaseER # Array of payoffs per target share
    NocPTTmean = np.mean(NocPTT)
    NocPTTstd = np.std(NocPTT)
    NocPTTmin = np.min(NocPTT)
    NocPTTmax = np.max(NocPTT)

    if collar_type == 'FEX':
        
        # SECTION 3. DEAL WITH FEX COLLAR

        # 3.1. Required assumptions
        FexLB = float(request.POST.get("fexLB")) # SEC
        FexUB = float(request.POST.get("fexUB")) # SEC

        # 3.2. Back-end calculations
        FexLL = SBTeff_array < FexLB # Bool array that the price is below the interval
        FexMU = SBTeff_array > FexUB # Bool array that the price is above the interval
        FexINS = np.logical_and(SBTeff_array >= FexLB, SBTeff_array <= FexUB) # Bool array that the price is inside the interval
        FexOUT = np.invert(FexINS) # Bool array that the price is outside the interval

        FexPTT = FexLL * (FexLB * BaseER) \
        + FexINS * (SBTeff_array * BaseER) \
        + FexMU * (FexUB * BaseER) # Array of payoffs per target share

        FexPTTmean = np.mean(FexPTT)
        FexPTTstd = np.std(FexPTT)
        FexPTTmin = np.min(FexPTT)
        FexPTTmax = np.max(FexPTT)

        FexER = FexOUT * (FexPTT / SBTeff_array) \
        + FexINS * BaseER # Array of exchange ratios

        FexEmission = np.round(NT0 * FexER) # Array of emission volumes
        FexStakeOfTarget = FexEmission / (NB0 + FexEmission) # Array of target stakes

        FexCVTT = FexPTTmean - NocPTTmean # Value of collar agreement to target
        FexCVTTTotal = FexCVTT * NT0 # Value to whole equity
        FexCVTTRel = FexCVTT / ST0 # Value as % of pre-announcement price

        # SECTION 4. FEX COLLAR + WALKAWAY PROVISION

        # 4.1. Back-end calculations
        FexWPTT = FexOUT * np.maximum(ST0*(1+DP)-FexPTT,0) # Array of option payoffs to target
        FexIfTC = FexWPTT > 0 # Bool array: 1 if target cancelled, 0 if not

        FexWPBT = FexOUT * np.maximum(FexPTT-ST0*(1+RP),0) # Array of option payoffs to bidder
        FexIfBC = FexWPBT > 0 # Bool array: 1 if bidder cancelled, 0 if not

        FexIfDC = np.maximum(FexIfTC,FexIfBC) # If at least 1 side cancelled, deal stops
        FexIfDS = np.invert(FexIfDC)

        FexSuccessfulDealsNumber = len(FexIfDS[FexIfDS == 1])
        FexPsuc = FexSuccessfulDealsNumber / simulations

        FexWPPTT = FexPTT * FexIfDS # 0 if deal is cancelled, payoff to target if not
        FexWPPTT_Suc = FexWPPTT[FexWPPTT > 0] # Payoff ONLY in closed deals
        FexWPPTT_Suc_mean = np.mean(FexWPPTT_Suc)
        FexWPPTT_Suc_std = np.std(FexWPPTT_Suc)
        FexWPPTT_Suc_min = np.min(FexWPPTT_Suc)
        FexWPPTT_Suc_max = np.max(FexWPPTT_Suc)

        FexWVTT = np.mean(FexWPTT) # Average option payoff among simulations
        FexWVTTTotal = FexWVTT * NT0 # For the whole equity
        FexWVTTRel = FexWVTT / ST0 # As % of pre-announcement price

        FexWVBT = np.mean(FexWPBT) # Average option payoff among simulations
        FexWVBTTotal = FexWVBT * NT0 # For the whole equity
        FexWVBTRel = FexWVBT / (ST0 * (1+RP)) # As % of investment value

        FexNetWV = FexWVTT - FexWVBT # Net walkaway value to target

    elif collar_type == 'FP':

        # SECTION 5. DEAL WITH FP COLLAR

        # 5.1. Required assumptions
        BaseP = float(request.POST.get("baseP"))
        UR = float(request.POST.get("UR"))
        LR = float(request.POST.get("LR"))
        FpLB = BaseP / UR
        FpUB = BaseP / LR

        # 5.2. Back-end calculations
        FpLL = SBTeff_array < FpLB # Bool array that the price is below the interval
        FpMU = SBTeff_array > FpUB # Bool array that the price is above the interval
        FpINS = np.logical_and(SBTeff_array >= FpLB, SBTeff_array <= FpUB) # Bool array that the price is inside the interval
        FpOUT = np.invert(FpINS) # Bool array that the price is outside the interval

        FpPTT = FpLL * (SBTeff_array * UR) \
        + FpINS * BaseP \
        + FpMU * (SBTeff_array * LR) # Array of payoffs per target share

        FpPTTmean = np.mean(FpPTT)
        FpPTTstd = np.std(FpPTT)
        FpPTTmin = np.min(FpPTT)
        FpPTTmax = np.max(FpPTT)

        FpER = FpPTT / SBTeff_array # Array of exchange ratios

        FpEmission = np.round(NT0 * FpER) # Array of emission volumes
        FpStakeOfTarget = FpEmission / (NB0 + FpEmission) # Array of target stakes

        FpCVTT = FpPTTmean - NocPTTmean # Value of collar agreement to target
        FpCVTTTotal = FpCVTT * NT0 # Value to whole equity
        FpCVTTRel = FpCVTT / ST0 # Value as % of pre-announcement price

        # SECTION 6. FP COLLAR + WALKAWAY PROVISION

        # 6.1. Back-end calculations
        FpWPTT = FpOUT * np.maximum(ST0*(1+DP)-FpPTT,0) # Array of option payoffs to target
        FpIfTC = FpWPTT > 0 # Bool array: 1 if target cancelled, 0 if not

        FpWPBT = FpOUT * np.maximum(FpPTT-ST0*(1+RP),0) # Array of option payoffs to bidder
        FpIfBC = FpWPBT > 0 # Bool array: 1 if bidder cancelled, 0 if not

        FpIfDC = np.maximum(FpIfTC,FpIfBC) # If at least 1 side cancelled, deal stops
        FpIfDS = np.invert(FpIfDC)

        FpSuccessfulDealsNumber = len(FpIfDS[FpIfDS == 1])
        FpPsuc = FpSuccessfulDealsNumber / simulations

        FpWPPTT = FpPTT * FpIfDS # 0 if deal is cancelled, payoff to target if not
        FpWPPTT_Suc = FpWPPTT[FpWPPTT > 0] # Payoff ONLY in closed deals
        FpWPPTT_Suc_mean = np.mean(FpWPPTT_Suc)
        FpWPPTT_Suc_std = np.std(FpWPPTT_Suc)
        FpWPPTT_Suc_min = np.min(FpWPPTT_Suc)
        FpWPPTT_Suc_max = np.max(FpWPPTT_Suc)

        FpWVTT = np.mean(FpWPTT) # Average option payoff among simulations
        FpWVTTTotal = FpWVTT * NT0 # For the whole equity
        FpWVTTRel = FpWVTT / ST0 # As % of pre-announcement price

        FpWVBT = np.mean(FpWPBT) # Average option payoff among simulations
        FpWVBTTotal = FpWVBT * NT0 # For the whole equity
        FpWVBTRel = FpWVBT / (ST0 * (1+RP)) # As % of investment value

        FpNetWV = FpWVTT - FpWVBT # Net walkaway value to target

    """DATA SELECTION"""
    if collar_type == 'FEX':
        LB = FexLB
        UB = FexUB
        CollarPTT = FexPTT
        CollarPTTmean = FexPTTmean
        CollarER = FexER
        CollarStakeOfTarget = FexStakeOfTarget
        CollarEmission = FexEmission
        CollarWPPTT_Suc = FexWPPTT_Suc
        CollarWPPTT_Suc_mean = FexWPPTT_Suc_mean

    elif collar_type == 'FP':
        LB = FpLB
        UB = FpUB
        CollarPTT = FpPTT
        CollarPTTmean = FpPTTmean
        CollarER = FpER
        CollarStakeOfTarget = FpStakeOfTarget
        CollarEmission = FpEmission
        CollarWPPTT_Suc = FpWPPTT_Suc
        CollarWPPTT_Suc_mean = FpWPPTT_Suc_mean
    
    """CHARTS CONTROLS"""
    red = '#c20430'
    green = '#00833f'
    blue = '#0071ce'
    orange = '#f98e2b'
    nbins = int(np.sqrt(simulations))

    """CHART 1"""
    chart1 = figure()

    for z in range(11):

        t_test = np.linspace(0, T, GBMsteps)
        N_test = np.random.standard_normal(size = GBMsteps)
        R_test = (t_test != 0) * (RetB * dt * t_test + StdB * np.cumsum(N_test) * np.sqrt(dt))
        SB_path_test = SB0 * (1 + R_test)
        chart1.line(t, SB_path_test, line_width=1, line_color=Paired12[z])

    chart1_start_price_line = Span(location=SB0,
                                   dimension='width', line_color='grey',
                                   line_dash='dashed', line_width=3)
    chart1.add_layout(chart1_start_price_line)

    chart1_upper_price_line = Span(location=UB,
                                   dimension='width', line_color=blue, line_width=3)
    chart1.add_layout(chart1_upper_price_line)

    chart1_lower_price_line = Span(location=LB,
                                   dimension='width', line_color=blue, line_width=3)
    chart1.add_layout(chart1_lower_price_line)

    chart1_interval_span = BoxAnnotation(bottom=LB, top=UB, fill_alpha=0.1, fill_color=blue)
    chart1.add_layout(chart1_interval_span)

    chart1_avgper_span = BoxAnnotation(left=T-avgper, right=T, fill_alpha=0.1, fill_color=red)
    chart1.add_layout(chart1_avgper_span)

    chart1.title.text = "1. Simulation modeling of bidder stock price"
    chart1.xaxis.axis_label = 'Days after signing merger agreement'
    chart1.yaxis.axis_label = 'Price, $'
    chart1.xgrid.grid_line_color = None
    chart1.ygrid.grid_line_color = None
    
    """CHART 2"""
    chart2 = figure()

    chart2_hist, chart2_edges = np.histogram(SBTeff_array, density=True, bins=nbins)
    chart2.quad(top=chart2_hist, bottom=0, left=chart2_edges[:-1], right=chart2_edges[1:],
                fill_color=red, line_color=red)

    chart2_span = BoxAnnotation(left=LB, right=UB, fill_alpha=0.1, fill_color=blue)
    chart2.add_layout(chart2_span)

    chart2_upper_price_line = Span(location=UB,
                                   dimension='height', line_color=blue, line_width=3)
    chart2.add_layout(chart2_upper_price_line)

    chart2_lower_price_line = Span(location=LB,
                                   dimension='height', line_color=blue, line_width=3)
    chart2.add_layout(chart2_lower_price_line)

    chart2.title.text = "2. Effective price distibution"
    chart2.xaxis.axis_label = 'Effective price'
    chart2.yaxis.axis_label = 'Probability'
    chart2.xgrid.grid_line_color = None
    chart2.ygrid.grid_line_color = None
    chart2.y_range.start = 0

    """CHART 3"""
    chart3 = figure(y_range=(0,0.2))
    
    chart3_hist_noc, chart3_edges_noc = np.histogram(NocPTT, density=True, bins=nbins)
    chart3.quad(top=chart3_hist_noc, bottom=0, left=chart3_edges_noc[:-1], right=chart3_edges_noc[1:],
                fill_color=red, line_color=red, legend_label="No collar")

    chart3_hist_collar, chart3_edges_collar = np.histogram(CollarPTT, density=True, bins=nbins)
    chart3.quad(top=chart3_hist_collar, bottom=0, left=chart3_edges_collar[:-1], right=chart3_edges_collar[1:],
                fill_color=green, line_color=green, legend_label="With collar")

    chart3_nocpttmean_line = Span(location=NocPTTmean, line_dash='dashed',
                                  dimension='height', line_color=red, line_width=3)
    chart3.add_layout(chart3_nocpttmean_line)

    chart3_collarpttmean_line = Span(location=CollarPTTmean, line_dash='dashed',
                                  dimension='height', line_color=green, line_width=3)
    chart3.add_layout(chart3_collarpttmean_line)

    chart3.title.text = "3. Collar's effect on payoff"
    chart3.xaxis.axis_label = 'Payoff to target, $'
    chart3.yaxis.axis_label = 'Probability'
    chart3.xgrid.grid_line_color = None
    chart3.ygrid.grid_line_color = None

    """CHART 4"""
    chart4 = figure()
    chart4.y_range = Range1d(45, 59)
    chart4.line(SBTeff_array, CollarPTT, color = red, line_width=3)

    chart4.extra_y_ranges = {"right": Range1d(start=0.2, end=1)}
    chart4.add_layout(LinearAxis(y_range_name="right", axis_label='Exchange ratio', axis_label_text_color = green), 'right')

    chart4.line(SBTeff_array, CollarER, color = green, line_width=3, y_range_name="right")

    chart4.add_layout(chart2_span)
    chart4.add_layout(chart2_lower_price_line)
    chart4.add_layout(chart2_upper_price_line)

    chart4.title.text = "4. Payoff to target and exchange ratio"
    chart4.xaxis.axis_label = 'Effective price'
    chart4.yaxis[0].axis_label = 'Payoff to target, $'
    chart4.yaxis[0].axis_label_text_color = red

    """CHART 5"""
    chart5 = figure()
    chart5.y_range = Range1d(0.2, 0.5)
    chart5.line(SBTeff_array, CollarStakeOfTarget, color = red, line_width=3)

    chart5.extra_y_ranges = {"right": Range1d(start=400, end=800)}
    chart5.add_layout(LinearAxis(y_range_name="right", axis_label='Emission volume'), 'right')

    chart5.line(SBTeff_array, CollarEmission / 1000000, y_range_name="right", alpha = 0)

    chart5.add_layout(chart2_span)
    chart5.add_layout(chart2_lower_price_line)
    chart5.add_layout(chart2_upper_price_line)

    chart5.title.text = "5. Consolidated company equity"
    chart5.xaxis.axis_label = 'Effective price'
    chart5.yaxis[0].axis_label = "Target's stake"

    """CHART 6"""
    chart6 = figure(y_range=(0,0.2))

    chart6_hist_nowa, chart6_edges_nowa = np.histogram(CollarPTT, density=True, bins=nbins)
    chart6.quad(top=chart6_hist_nowa, bottom=0, left=chart6_edges_nowa[:-1], right=chart6_edges_nowa[1:],
                fill_color=red, line_color=red, legend_label="No WP")

    chart6_hist_wa, chart6_edges_wa = np.histogram(CollarWPPTT_Suc, density=True, bins=nbins)
    chart6.quad(top=chart6_hist_wa, bottom=0, left=chart6_edges_wa[:-1], right=chart6_edges_wa[1:],
                fill_color=green, line_color=green, legend_label="With WP")

    chart6_collarpttmean_line = Span(location=CollarPTTmean, line_dash='dashed',
                                     dimension='height', line_color=red, line_width=3)
    chart6.add_layout(chart6_collarpttmean_line)

    chart6_wapttmean_line = Span(location=CollarWPPTT_Suc_mean, line_dash='dashed',
                                     dimension='height', line_color=green, line_width=3)
    chart6.add_layout(chart6_wapttmean_line)

    chart6.title.text = "6. Walkaway's effect on payoff"
    chart6.xaxis.axis_label = 'Payoff to target, $'
    chart6.yaxis.axis_label = 'Probability'
    chart6.xgrid.grid_line_color = None
    chart6.ygrid.grid_line_color = None

    grid = gridplot([[chart1, chart2, chart3], [chart4, chart5, chart6]], plot_width=420, plot_height=300)
    script_grid, div_grid = components(grid)

    context = {
        'bidder_name': bidder_name,
        'target_name': target_name,
        'script_grid': script_grid,
        'div_grid': div_grid
    }

    return render(request, 'result.html', context)