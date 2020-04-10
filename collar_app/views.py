from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index.html')

def add_two_numbers(request):
    number1 = int(request.GET["number1"])
    number2 = int(request.GET["number2"])
    result = number1 + number2
    return render(request, 'result.html', {'result': result})