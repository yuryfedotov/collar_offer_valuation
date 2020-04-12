from django.shortcuts import render
from bokeh.plotting import figure
from bokeh.layouts import gridplot
from bokeh.embed import components
from bokeh.models import Span, BoxAnnotation, LinearAxis, Range1d
from bokeh.palettes import Paired12
import numpy as np

def index(request):
    return render(request, 'index.html')

def calculate_market_cap(request):
    
    # 1.1. Getting inputs

    bidder_name = "Hi" # str(request.POST.get("bidderName"))

    NB0 = 1490776763 # Bidder shares before the deal
    NT0 = 1877000000 / 1.357190 # Target shares before the deal

    SB0 = 107.15 # Bidder price 1 day prior to announcement
    ST0 = 32.34 * 1.357190 # Target price 1 day prior to announcement
    RetB = 0.000743111004211404 # Daily return of bidder during the bid period
    StdB =0.0117901150659526 # Daily std of bidder's return during the bid period
    DP = (35 / 32.34) - 1 # Minimum premium desired by target, to the pre-announcement price
    RP = 0.3 # Maximum premium bidder is ready to pay, to the pre-announcement price

    simulations = 100000 # Number of simulations in the model
    T = 183 # Days between merger agreement and deal closing
    dt = 1 # Always 1, as we use daily intervals
    GBMsteps = round(T/dt) # Number of discrete intervals of GBM
    avgper = 15 # Averaging period, according to collar agreement

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
    BaseER = 0.5

    # 2.2. Back-end calculations
    NocPTT = SBTeff_array * BaseER # Array of payoffs per target share
    NocPTTmean = np.mean(NocPTT)
    NocPTTstd = np.std(NocPTT)
    NocPTTmin = np.min(NocPTT)
    NocPTTmax = np.max(NocPTT)

    # SECTION 3. DEAL WITH FEX COLLAR

    # 3.1. Required assumptions
    FexLB = 94 # SEC
    FexUB = 114 # SEC

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

    chart1_upper_price_line = Span(location=FexUB,
                                   dimension='width', line_color=blue, line_width=3)
    chart1.add_layout(chart1_upper_price_line)

    chart1_lower_price_line = Span(location=FexLB,
                                   dimension='width', line_color=blue, line_width=3)
    chart1.add_layout(chart1_lower_price_line)

    chart1_interval_span = BoxAnnotation(bottom=FexLB, top=FexUB, fill_alpha=0.1, fill_color=blue)
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

    chart2_span = BoxAnnotation(left=FexLB, right=FexUB, fill_alpha=0.1, fill_color=blue)
    chart2.add_layout(chart2_span)

    chart2_upper_price_line = Span(location=FexUB,
                                   dimension='height', line_color=blue, line_width=3)
    chart2.add_layout(chart2_upper_price_line)

    chart2_lower_price_line = Span(location=FexLB,
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

    chart3_hist_fex, chart3_edges_fex = np.histogram(FexPTT, density=True, bins=nbins)
    chart3.quad(top=chart3_hist_fex, bottom=0, left=chart3_edges_fex[:-1], right=chart3_edges_fex[1:],
                fill_color=green, line_color=green, legend_label="With collar")

    chart3.title.text = "3. Collar's effect on payoff"
    chart3.xaxis.axis_label = 'Payoff to target, $'
    chart3.yaxis.axis_label = 'Probability'
    chart3.xgrid.grid_line_color = None
    chart3.ygrid.grid_line_color = None

    """CHART 4"""
    chart4 = figure()
    chart4.y_range = Range1d(45, 59)
    chart4.line(SBTeff_array, FexPTT, color = red, line_width=3)

    chart4.extra_y_ranges = {"right": Range1d(start=0.2, end=1)}
    chart4.add_layout(LinearAxis(y_range_name="right", axis_label='Exchange ratio', axis_label_text_color = green), 'right')

    chart4.line(SBTeff_array, FexER, color = green, line_width=3, y_range_name="right")

    chart4.add_layout(chart2_span)
    chart4.add_layout(chart2_lower_price_line)
    chart4.add_layout(chart2_upper_price_line)

    chart4.title.text = "4. Payoff to target and exchange ratio"
    chart4.xaxis.axis_label = 'Effective price'
    chart4.yaxis[0].axis_label = 'Payoff to target, $'
    chart4.yaxis[0].axis_label_text_color = red

    """CHART 5"""
    chart5 = figure()
    chart5.line([1,2], [3,4], line_width=2, line_color='orange')

    chart6 = figure()
    chart6.line([1,2], [3,4], line_width=2, line_color='yellow')

    grid = gridplot([[chart1, chart2, chart3], [chart4, chart5, chart6]], plot_width=420, plot_height=300)
    script_grid, div_grid = components(grid)

    context = {
        'script_grid': script_grid,
        'div_grid': div_grid
    }

    return render(request, 'result.html', context)