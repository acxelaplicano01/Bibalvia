from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('sector/<int:id>/', views.sector_detail, name='sector_detail'),
    path('sector/nuevo/', views.sector_create, name='sector_create'),
]
