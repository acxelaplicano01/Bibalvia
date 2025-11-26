from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from dashboard import api_views
from dashboard import views

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
        # Imágenes
    path('upload-imagen/', views.upload_imagen_sector, name='upload_imagen_sector'),
    path('borrar-imagen/', views.borrar_imagen_sector, name='borrar_imagen_sector'),
    
    # Endpoints de sensores (LOCAL)
    path('iniciar-lectura/', views.iniciar_lectura_sensores, name='iniciar_lectura_sensores'),
    path('detener-lectura/', views.detener_lectura_sensores, name='detener_lectura_sensores'),
    path('stream-sensores/', views.stream_sensores, name='stream_sensores'),
    
    # API Endpoints (CLOUD)
    path('api/test/', api_views.test_api, name='api_test'),
    path('api/lectura/', api_views.recibir_lectura, name='api_recibir_lectura'),
    path('api/crear-sector/', api_views.crear_sector_remoto, name='api_crear_sector'),
    path('api/crear-zona/', api_views.crear_zona_remota, name='api_crear_zona'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


