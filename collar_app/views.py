from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

def calculate_market_cap(request):
    company_name = request.POST.get("bidderName")
    nshares = int(request.POST.get("bidderSharesBefore"))
    share_price = float(request.POST.get("bidderPriceBefore"))
    market_cap = nshares * share_price
    context = {
        'company_name': company_name,
        'market_cap': market_cap,
    }
    return render(request, 'result.html', context)