from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils import timezone
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
        
        # Guardar cada lectura
        HistorialTemperatura.objects.create(
            sector=sector,
            valor=data['temperatura'],
            marca_tiempo=data['marca_tiempo']
        )
        
        HistorialSalinidad.objects.create(
            sector=sector,
            valor=data['salinidad'],
            marca_tiempo=data['marca_tiempo']
        )
        
        HistorialPh.objects.create(
            sector=sector,
            valor=data['ph'],
            marca_tiempo=data['marca_tiempo']
        )
        
        HistorialTurbidez.objects.create(
            sector=sector,
            valor=data['turbidez'],
            marca_tiempo=data['marca_tiempo']
        )
        
        HistorialHumedad.objects.create(
            sector=sector,
            valor=data['humedad'],
            marca_tiempo=data['marca_tiempo']
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
    return Response({
        'status': 'ok',
        'mensaje': 'API funcionando correctamente',
        'entorno': settings.ENVIRONMENT,
        'timestamp': timezone.now().isoformat()
    })