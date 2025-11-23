from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from dashboard.models import Sector, Zona, HistorialTemperatura, HistorialSalinidad, HistorialPh, HistorialTurbidez, HistorialHumedad
from dashboard.serializers import LecturaSerializer

@api_view(['POST'])
def crear_sector_remoto(request):
    """Crea un sector desde LOCAL a CLOUD"""
    if not settings.IS_CLOUD:
        return Response({'error': 'Solo en cloud'}, status=403)
    
    api_key = request.headers.get('X-API-Key')
    if api_key != settings.CLOUD_API_KEY:
        return Response({'error': 'API Key inválida'}, status=401)
    
    try:
        data = request.data
        
        sector = Sector.objects.create(
            latitud=float(data['latitud']),
            longitud=float(data['longitud']),
            nombre_sector=data.get('nombre_sector')
        )
        
        # Asociar zonas si existen
        if data.get('zonas_ids'):
            sector.zonas.set(data['zonas_ids'])
        
        print(f"✓ Sector {sector.id} creado en la nube: {sector.nombre_sector or 'Sin nombre'}")
        
        return Response({
            'status': 'success',
            'sector_id': sector.id,
            'mensaje': 'Sector creado en la nube'
        }, status=201)
        
    except Exception as e:
        print(f"✗ Error al crear sector: {e}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def crear_zona_remota(request):
    """Crea una zona desde LOCAL a CLOUD"""
    if not settings.IS_CLOUD:
        return Response({'error': 'Solo en cloud'}, status=403)
    
    api_key = request.headers.get('X-API-Key')
    if api_key != settings.CLOUD_API_KEY:
        return Response({'error': 'API Key inválida'}, status=401)
    
    try:
        data = request.data
        
        # Verificar si ya existe
        zona_existente = Zona.objects.filter(nombre=data['nombre']).first()
        if zona_existente:
            return Response({
                'status': 'exists',
                'zona_id': zona_existente.id,
                'mensaje': f'Zona "{data["nombre"]}" ya existe'
            }, status=200)
        
        zona = Zona.objects.create(
            nombre=data['nombre'],
            geopoligono=data['geopoligono']
        )
        
        print(f"✓ Zona {zona.id} creada en la nube: {zona.nombre}")
        
        return Response({
            'status': 'success',
            'zona_id': zona.id,
            'mensaje': 'Zona creada en la nube'
        }, status=201)
        
    except Exception as e:
        print(f"✗ Error al crear zona: {e}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
def recibir_lectura(request):
    """Endpoint para recibir lecturas desde la Raspberry Pi"""
    if not settings.IS_CLOUD:
        return Response({'error': 'Solo en cloud'}, status=403)
    
    api_key = request.headers.get('X-API-Key')
    if api_key != settings.CLOUD_API_KEY:
        return Response({'error': 'API Key inválida'}, status=401)
    
    serializer = LecturaSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    data = serializer.validated_data
    
    try:
        sector = Sector.objects.get(id=data['sector_id'])
        marca_tiempo = data['marca_tiempo']
        guardados = 0
        
        # Guardar cada sensor que tenga datos
        if data.get('temperatura') is not None:
            HistorialTemperatura.objects.create(
                sector=sector, valor=data['temperatura'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if data.get('salinidad') is not None:
            HistorialSalinidad.objects.create(
                sector=sector, valor=data['salinidad'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if data.get('ph') is not None:
            HistorialPh.objects.create(
                sector=sector, valor=data['ph'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if data.get('turbidez') is not None:
            HistorialTurbidez.objects.create(
                sector=sector, valor=data['turbidez'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if data.get('humedad') is not None:
            HistorialHumedad.objects.create(
                sector=sector, valor=data['humedad'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        print(f"✓ {guardados} lecturas guardadas en PostgreSQL para sector {sector.id}")
        
        return Response({
            'status': 'success',
            'mensaje': f'Lectura guardada ({guardados} registros)'
        }, status=201)
        
    except Sector.DoesNotExist:
        return Response({'error': f'Sector {data["sector_id"]} no existe'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def test_api(request):
    """Endpoint de prueba"""
    from django.utils import timezone
    return Response({
        'status': 'ok',
        'mensaje': 'API funcionando correctamente',
        'entorno': settings.ENVIRONMENT,
        'timestamp': timezone.now().isoformat()
    })