from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('calculate_market_cap', views.calculate_market_cap, name='calculate_market_cap')
]