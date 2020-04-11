from django.shortcuts import render
from bokeh.plotting import figure
from bokeh.layouts import gridplot
from bokeh.embed import components

def index(request):
    return render(request, 'index.html')

def calculate_market_cap(request):
    
    """ WORKED
    company_name = str(request.POST.get("bidderName"))
    nshares = int(request.POST.get("bidderSharesBefore"))
    share_price = float(request.POST.get("bidderPriceBefore"))
    market_cap = nshares * share_price
    context = {
        'company_name': company_name,
        'market_cap': market_cap,
    }
    """
    
    company_name = str(request.POST.get("bidderName"))
    nshares = int(request.POST.get("bidderSharesBefore"))
    share_price = float(request.POST.get("bidderPriceBefore"))
    market_cap = nshares * share_price

    chart1 = figure()
    chart1.line([1,2], [nshares, share_price], line_width=2, line_color='blue')

    chart2 = figure()
    chart2.line([1,2], [nshares, share_price], line_width=2, line_color='red')

    chart3 = figure()
    chart3.line([1,2], [nshares, share_price], line_width=2, line_color='green')

    chart4 = figure()
    chart4.line([1,2], [nshares, share_price], line_width=2, line_color='purple')

    grid = gridplot([[chart1, chart2, None], [chart3, None, chart4]], plot_width=300, plot_height=250)
    script_grid, div_grid = components(grid)

    context = {
        'company_name': company_name,
        'market_cap': market_cap,
        'script_grid': script_grid,
        'div_grid': div_grid
    }

    return render(request, 'result.html', context)