from django.urls import path
from . import views
from .auth_views import login_view, logout_view

urlpatterns = [
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('home/', views.home, name='home'),
    path('sector/<int:id>/', views.sector_detail, name='sector_detail'),
    path('sector/nuevo/', views.sector_create, name='sector_create'),
    path('upload-imagen/', views.upload_imagen_sector, name='upload_imagen_sector'),
    path('borrar-imagen/', views.borrar_imagen_sector, name='borrar_imagen_sector'),
]
