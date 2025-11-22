from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from dashboard.models import Sector, HistorialTemperatura, HistorialSalinidad, HistorialPh, HistorialTurbidez, HistorialHumedad
from dashboard.serializers import LecturaSerializer

@api_view(['POST'])
def recibir_lectura(request):
    """
    Endpoint para recibir lecturas desde la Raspberry Pi.
    Solo funciona en modo CLOUD.
    """
    if not settings.IS_CLOUD:
        return Response(
            {'error': 'Este endpoint solo está disponible en modo CLOUD'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validar API Key
    api_key = request.headers.get('X-API-Key')
    
    
    # DEBUG (TEMPORAL - QUITAR EN PRODUCCIÓN)
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"API Key recibida: [{api_key}]")
    logger.error(f"API Key esperada: [{settings.CLOUD_API_KEY}]")
    logger.error(f"Longitud recibida: {len(api_key) if api_key else 0}")
    logger.error(f"Longitud esperada: {len(settings.CLOUD_API_KEY)}")
    logger.error(f"Son iguales: {api_key == settings.CLOUD_API_KEY}")
    
    if api_key != settings.CLOUD_API_KEY:
        return Response(
            {
                'error': 'API Key inválida',
                'debug': {  # TEMPORAL
                    'recibida_length': len(api_key) if api_key else 0,
                    'esperada_length': len(settings.CLOUD_API_KEY)
                }
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    
    if api_key != settings.CLOUD_API_KEY:
        return Response(
            {'error': 'API Key inválida'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    serializer = LecturaSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    
    try:
        sector = Sector.objects.get(id=data['sector_id'])
        
        marca_tiempo = data['marca_tiempo']
        
        # Guardar temperatura si existe
        if data.get('temperatura') is not None:
            HistorialTemperatura.objects.create(
                sector=sector,
                valor=data['temperatura'],
                marca_tiempo=marca_tiempo
            )
        
        # Guardar salinidad si existe
        if data.get('salinidad') is not None:
            HistorialSalinidad.objects.create(
                sector=sector,
                valor=data['salinidad'],
                marca_tiempo=marca_tiempo
            )
        
        # Guardar pH si existe
        if data.get('ph') is not None:
            HistorialPh.objects.create(
                sector=sector,
                valor=data['ph'],
                marca_tiempo=marca_tiempo
            )
        
        # Guardar turbidez si existe
        if data.get('turbidez') is not None:
            HistorialTurbidez.objects.create(
                sector=sector,
                valor=data['turbidez'],
                marca_tiempo=marca_tiempo
            )
        
        # Guardar humedad si existe
        if data.get('humedad') is not None:
            HistorialHumedad.objects.create(
                sector=sector,
                valor=data['humedad'],
                marca_tiempo=marca_tiempo
            )
        
        return Response(
            {'status': 'success', 'mensaje': 'Lectura guardada correctamente'},
            status=status.HTTP_201_CREATED
        )
        
    except Sector.DoesNotExist:
        return Response(
            {'error': f'Sector {data["sector_id"]} no existe'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def test_api(request):
    """
    Endpoint simple para probar que la API funciona.
    """
    from django.utils import timezone
    return Response({
        'status': 'ok',
        'mensaje': 'API funcionando correctamente',
        'entorno': settings.ENVIRONMENT,
        'timestamp': timezone.now().isoformat()
    })