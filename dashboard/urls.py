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
    
    # Endpoints de sensores (LOCAL)
    path('stream-sensores/', views.stream_sensores, name='stream_sensores'),
    path('iniciar-sensores/', views.iniciar_sensores, name='iniciar_sensores'),
    path('detener-sensores/', views.detener_sensores, name='detener_sensores'),
    path('iniciar-grabacion/', views.iniciar_grabacion, name='iniciar_grabacion'),
    path('detener-grabacion/', views.detener_grabacion, name='detener_grabacion'),
    
    # Exportar a csv
    path('exportar-csv/<int:sector_id>/', views.exportar_csv, name='exportar_csv'),
]

