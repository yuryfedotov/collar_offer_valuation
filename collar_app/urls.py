from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('add_two_numbers', views.add_two_numbers, name='add_two_numbers')
]