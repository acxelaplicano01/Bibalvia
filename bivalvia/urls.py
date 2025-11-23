"""
URL configuration for bivalvia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
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


