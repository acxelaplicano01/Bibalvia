import os
import json
import re
import serial
import time
import requests
from django.utils import timezone
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render, redirect
from dashboard.models import Sector, Zona
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required

# Configuración serial
SERIAL_PORT = '/dev/ttyACM0'  # Ajustar: Windows=COM3, Linux=/dev/ttyACM0
BAUD_RATE = 9600
TIMEOUT = 3

lectura_activa = False
conexion_serial = None

@login_required
def home(request):
    sectores = Sector.objects.all()
    context = {
        'sectores': sectores,
    }
    
    toast = request.GET.get('toast')
    toast_tipo = request.GET.get('toast_tipo', 'success')
    
    if toast:
        context['toast'] = toast
        context['toast_tipo'] = toast_tipo
    
    return render(request, 'dashboard/home.html', context)

@login_required
def sector_detail(request, id):
    sector = Sector.objects.prefetch_related('zonas').get(id=id)

    # Obtener últimas lecturas
    ultima_temperatura = sector.temperaturas.order_by('-marca_tiempo').first()
    ultima_salinidad = sector.salinidades.order_by('-marca_tiempo').first()
    ultima_ph = sector.ph_registros.order_by('-marca_tiempo').first()
    ultima_turbidez = sector.turbideces.order_by('-marca_tiempo').first()
    ultima_humedad = sector.humedades.order_by('-marca_tiempo').first()

    carpeta = os.path.join(settings.MEDIA_ROOT, 'sectores')
    imagenes = []
    siguiente_num = 1

    if os.path.exists(carpeta):
        imagenes = [
            img for img in os.listdir(carpeta)
            if f'sector{id}' in img
        ]

        numeros = []
        for img in imagenes:
            match = re.search(rf'sector{id}-imagen(\d+)', img)
            if match:
                numeros.append(int(match.group(1)))
        
        if numeros:
            siguiente_num = max(numeros) + 1

    context = {
        'sector': sector,
        'imagenes': imagenes,
        'MEDIA_URL': settings.MEDIA_URL,
        'siguiente_num': siguiente_num,
        # Datos de sensores
        'ultima_temperatura': ultima_temperatura,
        'ultima_salinidad': ultima_salinidad,
        'ultima_ph': ultima_ph,
        'ultima_turbidez': ultima_turbidez,
        'ultima_humedad': ultima_humedad,
    }
    return render(request, 'dashboard/sector_detail.html', context)

@login_required
def sector_create(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        
        if tipo == 'zona':
            nombre = request.POST.get('nombre')
            coordenadas = request.POST.get('coordenadas')
            
            if nombre and coordenadas:
                try:
                    coords_json = json.loads(coordenadas)
                    geojson = {
                        "type": "Polygon",
                        "coordinates": [[
                            [coord['lng'], coord['lat']] for coord in coords_json
                        ] + [[coords_json[0]['lng'], coords_json[0]['lat']]]]
                    }
                    
                    # Crear en LOCAL
                    zona = Zona.objects.create(nombre=nombre, geopoligono=geojson)
                    
                    # Sincronizar con CLOUD si estamos en LOCAL
                    if settings.IS_LOCAL:
                        sincronizar_zona_a_nube(zona)
                    
                    return JsonResponse({
                        'success': True,
                        'mensaje': f'Zona "{nombre}" creada exitosamente',
                        'zona': {
                            'id': zona.id,
                            'nombre': zona.nombre,
                            'geopoligono': zona.geopoligono
                        }
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'mensaje': f'Error: {str(e)}'
                    }, status=400)
        
        elif tipo == 'punto':
            latitud = request.POST.get('latitud')
            longitud = request.POST.get('longitud')
            nombre_sector = request.POST.get('nombre_sector')
            zonas_ids = request.POST.get('zonas_ids', '')
            
            if latitud and longitud:
                try:
                    # Crear en LOCAL
                    sector = Sector.objects.create(
                        latitud=float(latitud),
                        longitud=float(longitud),
                        nombre_sector=nombre_sector if nombre_sector else None
                    )
                    
                    if zonas_ids:
                        zona_ids_list = [int(id) for id in zonas_ids.split(',') if id]
                        sector.zonas.set(zona_ids_list)
                    
                    # Sincronizar con CLOUD si estamos en LOCAL
                    if settings.IS_LOCAL:
                        sincronizar_sector_a_nube(sector)
                    
                    messages.success(request, f'Sector creado exitosamente')
                    return redirect('home')
                    
                except ValueError:
                    messages.error(request, 'Coordenadas inválidas')
                    return redirect('home')
    
    zonas = Zona.objects.all()
    context = {
        'zonas': list(zonas.values('id', 'nombre', 'geopoligono'))
    }
    return render(request, 'dashboard/sector_create.html', context)

def sincronizar_sector_a_nube(sector):
    """Sincroniza un sector LOCAL con CLOUD"""
    if not settings.IS_LOCAL:
        return False
    
    if not settings.CLOUD_API_URL or not settings.CLOUD_API_KEY:
        print("⚠️ No hay configuración de nube")
        return False
    
    try:
        payload = {
            'latitud': float(sector.latitud),
            'longitud': float(sector.longitud),
            'nombre_sector': sector.nombre_sector,
            'zonas_ids': list(sector.zonas.values_list('id', flat=True))
        }
        
        headers = {
            'X-API-Key': settings.CLOUD_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{settings.CLOUD_API_URL}/crear-sector/",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Sector sincronizado con la nube (ID cloud: {data.get('sector_id')})")
            return True
        else:
            print(f"✗ Error al sincronizar sector: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error al sincronizar sector: {e}")
        return False
    
    
def sincronizar_zona_a_nube(zona):
    """Sincroniza una zona LOCAL con CLOUD"""
    if not settings.IS_LOCAL:
        return False
    
    if not settings.CLOUD_API_URL or not settings.CLOUD_API_KEY:
        print("⚠️ No hay configuración de nube")
        return False
    
    try:
        payload = {
            'nombre': zona.nombre,
            'geopoligono': zona.geopoligono
        }
        
        headers = {
            'X-API-Key': settings.CLOUD_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{settings.CLOUD_API_URL}/crear-zona/",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            print(f"✓ Zona sincronizada con la nube (ID cloud: {data.get('zona_id')})")
            return True
        else:
            print(f"✗ Error al sincronizar zona: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error al sincronizar zona: {e}")
        return False
    
    
@login_required
@csrf_exempt
def upload_imagen_sector(request):
    if request.method == 'POST':
        imagen = request.FILES['imagen']
        
        # No se necesita porque en el nombre de la imagen va el id
        # sector_id = request.POST.get('sector_id')

        fs = FileSystemStorage(location='media/sectores/')
        filename = fs.save(imagen.name, imagen)

        return JsonResponse({'ok': True, 'filename': filename})

@login_required  
@csrf_exempt
def borrar_imagen_sector(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        nombre = data.get('nombre')

        path = os.path.join(settings.MEDIA_ROOT, 'sectores', nombre)
        if os.path.exists(path):
            os.remove(path)
            return JsonResponse({'ok': True})

    return JsonResponse({'ok': False})


def conectar_arduino():
    global conexion_serial
    try:
        if conexion_serial is None or not conexion_serial.is_open:
            conexion_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
            time.sleep(5)
        return True
    except serial.SerialException as e:
        print(f"Error conectando Arduino: {e}")
        return False

def leer_datos_arduino():
    global conexion_serial
    
    if conexion_serial is None or not conexion_serial.is_open:
        if not conectar_arduino():
            return None
    
    try:
        conexion_serial.reset_input_buffer()
        conexion_serial.write(b'R')
        linea = conexion_serial.readline().decode('utf-8').strip()
        
        if linea:
            datos = json.loads(linea)
            return datos
    except Exception as e:
        print(f"Error leyendo datos: {e}")
        return None
    
    return None

@csrf_exempt
@require_http_methods(["POST"])
def iniciar_lectura_sensores(request):
    global lectura_activa
    lectura_activa = True
    
    if not conectar_arduino():
        return JsonResponse({
            'error': 'No se pudo conectar con Arduino en el puerto serial.'
        }, status=500)
    
    return JsonResponse({'status': 'iniciado'})

@csrf_exempt
@require_http_methods(["POST"])
def detener_lectura_sensores(request):
    global lectura_activa, conexion_serial
    lectura_activa = False
    
    if conexion_serial and conexion_serial.is_open:
        conexion_serial.close()
        conexion_serial = None
    
    return JsonResponse({'status': 'detenido'})

def stream_sensores(request):
    def event_stream():
        global lectura_activa
        
        sector_id = request.GET.get('sector_id')
        
        if not sector_id:
            yield f"data: {json.dumps({'error': 'Falta sector_id'})}\n\n"
            return
        
        while lectura_activa:
            datos = leer_datos_arduino()
            
            if datos:
                print(f"📊 Datos recibidos: {datos}")
                
                # 1. Enviar al navegador
                yield f"data: {json.dumps(datos)}\n\n"
                
                # 2. Guardar en base de datos local
                print(f"💾 Guardando en base de datos local...")
                guardar_lectura_local(datos, sector_id)
                
                # 3. Enviar a la nube si estamos en LOCAL
                if settings.IS_LOCAL:
                    print(f"☁️ Enviando a la nube...")
                    enviar_a_nube(datos, sector_id)
            else:
                yield f"data: {json.dumps({'error': 'Sin datos'})}\n\n"
            
            time.sleep(5)
        
        yield "data: {\"status\": \"cerrado\"}\n\n"
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def guardar_lectura_local(datos, sector_id):
    """Guarda lecturas en la base de datos LOCAL"""
    try:
        from dashboard.models import (
            Sector, HistorialTemperatura, HistorialSalinidad,
            HistorialPh, HistorialTurbidez, HistorialHumedad
        )
        
        sector = Sector.objects.get(id=sector_id)
        marca_tiempo = timezone.now()
        guardados = 0
        
        if datos.get('temperatura') is not None and datos['temperatura'] != -999:
            HistorialTemperatura.objects.create(
                sector=sector, valor=datos['temperatura'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if datos.get('ph') is not None:
            HistorialPh.objects.create(
                sector=sector, valor=datos['ph'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if datos.get('turbidez') is not None:
            HistorialTurbidez.objects.create(
                sector=sector, valor=datos['turbidez'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if datos.get('humedad') is not None:
            HistorialHumedad.objects.create(
                sector=sector, valor=datos['humedad'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        if datos.get('salinidad') is not None:
            HistorialSalinidad.objects.create(
                sector=sector, valor=datos['salinidad'], marca_tiempo=marca_tiempo
            )
            guardados += 1
        
        print(f"💾 {guardados} lecturas guardadas en SQLite local")
        return True
        
    except Sector.DoesNotExist:
        print(f"❌ Sector {sector_id} no existe en local")
        return False
    except Exception as e:
        print(f"❌ Error al guardar local: {e}")
        return False

def enviar_a_nube(datos, sector_id):
    """Envía datos a la instancia en la nube"""
    if not settings.CLOUD_API_URL or not settings.CLOUD_API_KEY:
        print("⚠️ No hay configuración de nube")
        return False
    
    try:
        payload = {
            'sector_id': int(sector_id),
            'temperatura': float(datos.get('temperatura')) if datos.get('temperatura') is not None else None,
            'salinidad': None,  # Si tienes sensor de salinidad, agrégalo
            'ph': float(datos.get('ph')) if datos.get('ph') is not None else None,
            'turbidez': float(datos.get('turbidez')) if datos.get('turbidez') is not None else None,
            'humedad': float(datos.get('humedad')) if datos.get('humedad') is not None else None,
            'marca_tiempo': timezone.now().isoformat()
        }
        
        headers = {
            'X-API-Key': settings.CLOUD_API_KEY,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            f"{settings.CLOUD_API_URL}/lectura/",
            json=payload,
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 201:
            print(f"✓ Datos enviados a la nube: T={datos.get('temperatura')}°C")
            return True
        else:
            print(f"✗ Error al enviar a nube: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión con la nube: {e}")
        return False
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        return False