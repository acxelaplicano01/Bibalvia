from django.urls import path
from . import views
from .auth_views import login_view, logout_view
from . import api_views

urlpatterns = [
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('sector/<int:id>/', views.sector_detail, name='sector_detail'),
    path('sector/nuevo/', views.sector_create, name='sector_create'),
]

