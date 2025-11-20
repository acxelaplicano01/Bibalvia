import os
import json
import re
import serial
import time
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render, redirect
from dashboard.models import Sector, Zona
from django.views.decorators.http import require_POST
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
    sector = Sector.objects.get(id=id)

    carpeta = os.path.join(settings.MEDIA_ROOT, 'sectores')
    imagenes = []
    siguiente_num = 1   # contador por defecto

    if os.path.exists(carpeta):
        imagenes = [
            img for img in os.listdir(carpeta)
            if f'sector{id}' in img
        ]

        # Buscar el número más alto de imagenX
        numeros = []
        for img in imagenes:
            # CORREGIDO: buscar sector{id}-imagen{num}
            match = re.search(rf'sector{id}-imagen(\d+)', img)
            if match:
                numeros.append(int(match.group(1)))
        
        if numeros:
            siguiente_num = max(numeros) + 1

    context = {
        'sector': sector,
        'imagenes': imagenes,
        'MEDIA_URL': settings.MEDIA_URL,
        'siguiente_num': siguiente_num
    }
    return render(request, 'dashboard/sector_detail.html', context)

@login_required
def sector_create(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')
        
        if tipo == 'zona':
            # Guardar nueva zona
            nombre = request.POST.get('nombre')
            coordenadas = request.POST.get('coordenadas')
            
            if nombre and coordenadas:
                try:
                    coords_json = json.loads(coordenadas)
                    # Convertir a formato GeoJSON
                    geojson = {
                        "type": "Polygon",
                        "coordinates": [[
                            [coord['lng'], coord['lat']] for coord in coords_json
                        ] + [[coords_json[0]['lng'], coords_json[0]['lat']]]]  # Cerrar el polígono
                    }
                    
                    zona = Zona.objects.create(
                        nombre=nombre,
                        geopoligono=geojson
                    )
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
                        'mensaje': f'Error al crear zona: {str(e)}'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'mensaje': 'Faltan datos para crear la zona'
                }, status=400)
        
        elif tipo == 'punto':
            # Guardar nuevo sector
            latitud = request.POST.get('latitud')
            longitud = request.POST.get('longitud')
            nombre_sector = request.POST.get('nombre_sector')
            zonas_ids = request.POST.get('zonas_ids', '')
            
            if latitud and longitud:
                try:
                    sector = Sector.objects.create(
                        latitud=float(latitud),
                        longitud=float(longitud),
                        nombre_sector=nombre_sector if nombre_sector else None
                    )
                    
                    # Asociar zonas si existen
                    if zonas_ids:
                        zona_ids_list = [int(id) for id in zonas_ids.split(',') if id]
                        sector.zonas.set(zona_ids_list)
                    
                    return redirect(f'/?toast=Sector creado exitosamente en ({latitud}, {longitud})&toast_tipo=success')
                except ValueError:
                    return redirect('/?toast=Coordenadas inválidas&toast_tipo=error')
            else:
                return redirect('/?toast=Por favor selecciona una ubicación en el mapa&toast_tipo=error')
    
    # GET: Cargar todas las zonas
    zonas = Zona.objects.all()
    context = {
        'zonas': list(zonas.values('id', 'nombre', 'geopoligono'))
    }
    return render(request, 'dashboard/sector_create.html', context)


@login_required
@csrf_exempt
def upload_imagen_sector(request):
    if request.method == 'POST':
        imagen = request.FILES['imagen']
        sector_id = request.POST.get('sector_id')

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
        
        while lectura_activa:
            datos = leer_datos_arduino()
            
            if datos:
                yield f"data: {json.dumps(datos)}\n\n"
            else:
                yield f"data: {json.dumps({'error': 'Sin datos'})}\n\n"
            
            time.sleep(5)
        
        yield "data: {\"status\": \"cerrado\"}\n\n"
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response