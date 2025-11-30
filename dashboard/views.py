import os
import json
import re
import serial
import time
import requests
import asyncio
from django.utils import timezone
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render, redirect
from dashboard.models import Sector, Zona
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
import csv

# Importar cliente WebSocket solo en LOCAL
try:
    if settings.IS_LOCAL:
        from dashboard.ws_client import sensor_ws_client, enviar_a_nube_ws_sync
    else:
        sensor_ws_client = None
        enviar_a_nube_ws_sync = None
except (ImportError, AttributeError):
    sensor_ws_client = None
    enviar_a_nube_ws_sync = None

# Importar cliente WebSocket solo en LOCAL
if settings.IS_LOCAL:
    try:
        from dashboard.ws_client import sensor_ws_client, enviar_a_nube_ws_sync
    except ImportError:
        print("⚠️ ws_client no disponible")
        sensor_ws_client = None
        enviar_a_nube_ws_sync = None

# Configuración serial
# SERIAL_PORT = '/dev/ttyACM0'  # Ajustar: Windows=COM3, Linux=/dev/ttyACM0
SERIAL_PORT = 'COM3'  # Ajustar: Windows=COM3, Linux=/dev/ttyACM0
BAUD_RATE = 9600
TIMEOUT = 3

# Variables globales
lectura_activa = False
grabacion_activa = False
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
    """
    Vista de detalle del sector.
    """
    # ✅ AGREGAR ESTO AL INICIO
    if settings.IS_LOCAL:
        global lectura_activa
        if not lectura_activa:
            if conectar_arduino():
                lectura_activa = True
                print("✅ Arduino conectado automáticamente")
    
    sector = Sector.objects.prefetch_related('zonas').get(id=id)
    
    # Parámetros de filtro de fecha
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(hours=24)
    else:
        fecha_inicio = timezone.make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%dT%H:%M'))
        fecha_fin = timezone.make_aware(datetime.strptime(fecha_fin, '%Y-%m-%dT%H:%M'))
    
    # Todas las lecturas para la tabla
    temperaturas = sector.temperaturas.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    ).order_by('-marca_tiempo')
    ph_registros = sector.ph_registros.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    ).order_by('-marca_tiempo')
    turbideces = sector.turbideces.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    ).order_by('-marca_tiempo')
    humedades = sector.humedades.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    ).order_by('-marca_tiempo')
    
    # Diccionarios por marca de tiempo
    ph_dict = {r.marca_tiempo: r for r in ph_registros}
    turb_dict = {r.marca_tiempo: r for r in turbideces}
    hum_dict = {r.marca_tiempo: r for r in humedades}
    
    # Lecturas combinadas para la tabla
    lecturas_combinadas = []
    for temp in temperaturas:
        lecturas_combinadas.append({
            'marca_tiempo': temp.marca_tiempo,
            'temperatura': temp,
            'ph': ph_dict.get(temp.marca_tiempo),
            'turbidez': turb_dict.get(temp.marca_tiempo),
            'humedad': hum_dict.get(temp.marca_tiempo),
        })

    # Últimos valores (cards)
    ultima_temperatura = temperaturas.first()
    ultima_salinidad = sector.salinidades.order_by('-marca_tiempo').first()
    ultima_ph = ph_registros.first()
    ultima_turbidez = turbideces.first()
    ultima_humedad = humedades.first()
    
    # Últimos 20 registros para la chart - CONVERTIR A FLOAT
    MAX_POINTS = 20
    ultimas_temp = list(temperaturas[:MAX_POINTS])[::-1]
    ultimos_ph = list(ph_registros[:MAX_POINTS])[::-1]
    ultimas_turb = list(turbideces[:MAX_POINTS])[::-1]
    ultimas_hum = list(humedades[:MAX_POINTS])[::-1]
    
    chart_data = []
    for i in range(MAX_POINTS):
        temp_val = float(ultimas_temp[i].valor) if i < len(ultimas_temp) else 0
        ph_val = float(ultimos_ph[i].valor) if i < len(ultimos_ph) else 7
        turb_val = float(ultimas_turb[i].valor) if i < len(ultimas_turb) else 0
        hum_val = float(ultimas_hum[i].valor) if i < len(ultimas_hum) else 0
        
        chart_data.append({
            'marca_tiempo': ultimas_temp[i].marca_tiempo.strftime('%H:%M:%S') if i < len(ultimas_temp) else '',
            'temperatura': temp_val,
            'ph': ph_val,
            'turbidez': turb_val,
            'humedad': hum_val,
        })
    
    # Imágenes
    carpeta = os.path.join(settings.MEDIA_ROOT, 'sectores')
    imagenes = []
    siguiente_num = 1
    if os.path.exists(carpeta):
        imagenes = [img for img in os.listdir(carpeta) if f'sector{id}' in img]
        numeros = [int(re.search(rf'sector{id}-imagen(\d+)', img).group(1))
                   for img in imagenes if re.search(rf'sector{id}-imagen(\d+)', img)]
        if numeros:
            siguiente_num = max(numeros) + 1
    
    context = {
        'sector': sector,
        'imagenes': imagenes,
        'MEDIA_URL': settings.MEDIA_URL,
        'siguiente_num': siguiente_num,
        'ultima_temperatura': ultima_temperatura,
        'ultima_salinidad': ultima_salinidad,
        'ultima_ph': ultima_ph,
        'ultima_turbidez': ultima_turbidez,
        'ultima_humedad': ultima_humedad,
        'lecturas_combinadas': lecturas_combinadas,
        'chart_data_json': chart_data,
        'fecha_inicio': fecha_inicio.strftime('%Y-%m-%dT%H:%M'),
        'fecha_fin': fecha_fin.strftime('%Y-%m-%dT%H:%M'),
    }
    return render(request, 'dashboard/sector_detail.html', context)


@login_required
def sector_create(request):
    """
    Crear nuevo sector.
    
    Sin cambios - mantiene funcionalidad existente.
    """
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
            time.sleep(2)
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
def iniciar_sensores(request):
    global lectura_activa
    
    if not conectar_arduino():
        return JsonResponse({'error': 'No se pudo conectar con Arduino'}, status=500)
    
    lectura_activa = True
    print(f"✅ Sensores iniciados - lectura_activa = {lectura_activa}")
    
    return JsonResponse({'status': 'sensores_iniciados'})

@csrf_exempt
@require_http_methods(["POST"])
def detener_sensores(request):
    global lectura_activa, grabacion_activa, conexion_serial
    
    lectura_activa = False
    grabacion_activa = False
    
    print("🛑 Deteniendo sensores...")
    
    # Cerrar serial primero
    if conexion_serial and conexion_serial.is_open:
        try:
            conexion_serial.close()
            conexion_serial = None
            print("✅ Serial cerrado")
        except Exception as e:
            print(f"⚠️ Error cerrando serial: {e}")
    
    # NO cerrar WebSocket aquí (está causando el crash)
    # El WebSocket se cierra automáticamente cuando detener_grabacion()
    
    return JsonResponse({'status': 'sensores_detenidos'})

@csrf_exempt
@require_http_methods(["POST"])
def iniciar_grabacion(request):
    """Inicia guardado en DB y envío al cloud"""
    global grabacion_activa
    
    if not lectura_activa:
        return JsonResponse({'error': 'Debes iniciar los sensores primero'}, status=400)
    
    grabacion_activa = True
    
    # Conectar WebSocket
    if settings.IS_LOCAL and enviar_a_nube_ws_sync:
        try:
            import threading
            def start_ws():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(sensor_ws_client.connect())
            
            ws_thread = threading.Thread(target=start_ws, daemon=True)
            ws_thread.start()
            ws_thread.join(timeout=5)
        except Exception as e:
            print(f"⚠️ Error WebSocket: {e}")
    
    return JsonResponse({'status': 'grabacion_iniciada'})

@csrf_exempt
@require_http_methods(["POST"])
def detener_grabacion(request):
    """Detiene guardado pero mantiene lectura"""
    global grabacion_activa
    grabacion_activa = False
    
    # Cerrar WebSocket
    if settings.IS_LOCAL and sensor_ws_client and sensor_ws_client.connected:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(sensor_ws_client.disconnect())
            loop.close()
        except Exception as e:
            print(f"⚠️ Error: {e}")
    
    return JsonResponse({'status': 'grabacion_detenida'})

# def stream_sensores(request):
#     """SSE con flush explícito"""
    
#     def event_stream():
#         global lectura_activa, grabacion_activa
        
#         sector_id = request.GET.get('sector_id')
#         grabar = request.GET.get('grabar') == 'true'
        
#         print(f"🔌 SSE iniciado - sector:{sector_id}, grabar:{grabar}, lectura_activa:{lectura_activa}")
        
#         # Mensaje inicial con padding para forzar flush
#         yield ":\n\n"  # Comentario SSE (ignora el navegador)
#         yield f"data: {json.dumps({'status': 'conectado'})}\n\n"
        
#         if not sector_id:
#             yield f"data: {json.dumps({'error': 'Sin sector_id'})}\n\n"
#             return
        
#         contador = 0
#         while lectura_activa and contador < 500:
#             try:
#                 datos = leer_datos_arduino()
                
#                 if datos:
#                     print(f"📤 Enviando: temp={datos.get('temperatura')}")
                    
#                     # Formatear SSE correctamente
#                     mensaje = f"data: {json.dumps(datos)}\n\n"
#                     yield mensaje
                    
#                     # Si graba
#                     if grabar and grabacion_activa:
#                         marca_tiempo = timezone.now()
#                         guardar_lectura_local(datos, sector_id, marca_tiempo)
#                         print("💾 Guardado")
                
#                 else:
#                     yield "data: {\"heartbeat\": true}\n\n"
                    
#             except Exception as e:
#                 print(f"❌ Error: {e}")
#                 yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
#             contador += 1
#             time.sleep(2)
        
#         print("🔌 SSE cerrado")
#         yield "data: {\"status\": \"cerrado\"}\n\n"
    
#     response = StreamingHttpResponse(
#         event_stream(), 
#         content_type='text/event-stream; charset=utf-8'
#     )
#     response['Cache-Control'] = 'no-cache, no-transform'
#     response['X-Accel-Buffering'] = 'no'
#     response['Connection'] = 'keep-alive'
    
#     return response

# Nueva vista
@csrf_exempt
@require_http_methods(["GET"])
def obtener_lectura(request):
    """Obtiene una sola lectura actual"""
    global lectura_activa, grabacion_activa
    
    if not lectura_activa:
        return JsonResponse({'error': 'Sensores no activos'}, status=400)
    
    datos = leer_datos_arduino()
    
    if datos:
        sector_id = request.GET.get('sector_id')
        
        # Si está grabando, guardar Y enviar a cloud
        if grabacion_activa and sector_id:
            marca_tiempo = timezone.now()
            
            # Guardar local
            guardar_lectura_local(datos, sector_id, marca_tiempo)
            
            # Enviar a cloud
            if settings.IS_LOCAL and enviar_a_nube_ws_sync:
                enviar_a_nube_ws_sync(datos, sector_id, marca_tiempo)
        
        return JsonResponse(datos)
    else:
        return JsonResponse({'error': 'Sin datos'}, status=503)
    
    
# def stream_sensores(request):
#     """Versión SIMPLIFICADA - sin async, sin complicaciones"""
    
#     def event_stream():
#         global lectura_activa, grabacion_activa
        
#         sector_id = request.GET.get('sector_id')
#         grabar = request.GET.get('grabar') == 'true'
        
#         print(f"🔌 SSE iniciado - sector:{sector_id}, grabar:{grabar}, lectura_activa:{lectura_activa}")
        
#         # Mensaje inicial
#         yield f"data: {json.dumps({'status': 'conectado'})}\n\n"
        
#         if not sector_id:
#             yield f"data: {json.dumps({'error': 'Sin sector_id'})}\n\n"
#             return
        
#         contador = 0
#         while lectura_activa and contador < 500:
#             try:
#                 datos = leer_datos_arduino()
                
#                 if datos:
#                     print(f"📤 Enviando al navegador: {datos}")
#                     yield f"data: {json.dumps(datos)}\n\n"
                    
#                     # Solo guardar si está grabando
#                     if grabar and grabacion_activa:
#                         marca_tiempo = timezone.now()
#                         guardar_lectura_local(datos, sector_id, marca_tiempo)
#                         print("💾 Guardado en BD")
                        
#                         # SIN ENVÍO A CLOUD POR AHORA
#                         # Lo agregaremos después cuando esto funcione
                
#                 else:
#                     yield f"data: {json.dumps({'heartbeat': True})}\n\n"
                    
#             except Exception as e:
#                 print(f"❌ Error: {e}")
#                 yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
#             contador += 1
#             time.sleep(2)
        
#         print("🔌 SSE cerrado")
#         yield f"data: {json.dumps({'status': 'cerrado'})}\n\n"
    
#     response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
#     response['Cache-Control'] = 'no-cache'
#     response['X-Accel-Buffering'] = 'no'
#     return response



def guardar_lectura_local(datos, sector_id, marca_tiempo=None):
    """
    Guarda lecturas en la base de datos LOCAL.
    
    Sin cambios - mantiene compatibilidad.
    """
    try:
        from dashboard.models import (
            Sector, HistorialTemperatura, HistorialSalinidad,
            HistorialPh, HistorialTurbidez, HistorialHumedad
        )
        
        sector = Sector.objects.get(id=sector_id)
        
        # Usar timestamp proporcionado o generar uno nuevo
        if marca_tiempo is None:
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
        
        print(f"💾 {guardados} lecturas guardadas en local")
        return True
        
    except Sector.DoesNotExist:
        print(f"❌ Sector {sector_id} no existe en local")
        return False
    except Exception as e:
        print(f"❌ Error al guardar local: {e}")
        return False

def enviar_a_nube(datos, sector_id, marca_tiempo=None):
    """Envía datos a la instancia en la nube"""
    if not settings.CLOUD_API_URL or not settings.CLOUD_API_KEY:
        print("⚠️ No hay configuración de nube")
        return False
    
    try:
        # Usar timestamp proporcionado o generar uno nuevo
        if marca_tiempo is None:
            marca_tiempo = timezone.now()
        
        payload = {
            'sector_id': int(sector_id),
            'temperatura': float(datos.get('temperatura')) if datos.get('temperatura') is not None else None,
            'salinidad': None,
            'ph': float(datos.get('ph')) if datos.get('ph') is not None else None,
            'turbidez': float(datos.get('turbidez')) if datos.get('turbidez') is not None else None,
            'humedad': float(datos.get('humedad')) if datos.get('humedad') is not None else None,
            'marca_tiempo': marca_tiempo.isoformat()  # Usar el timestamp compartido
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
            print(f"✓ Datos enviados a la nube")
            return True
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Error de conexión: {e}")
        return False
    except Exception as e:
        print(f"✗ Error inesperado: {e}")
        return False
    
    
@login_required
def exportar_csv(request, sector_id):
    sector = Sector.objects.get(id=sector_id)
    
    # Filtros de fecha (igual que sector_detail)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if not fecha_inicio or not fecha_fin:
        fecha_fin = timezone.now()
        fecha_inicio = fecha_fin - timedelta(hours=24)
    else:
        fecha_inicio = timezone.make_aware(datetime.strptime(fecha_inicio, '%Y-%m-%dT%H:%M'))
        fecha_fin = timezone.make_aware(datetime.strptime(fecha_fin, '%Y-%m-%dT%H:%M'))
    
    # Obtener datos
    temperaturas = sector.temperaturas.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    ).order_by('-marca_tiempo')
    
    ph_dict = {r.marca_tiempo: r for r in sector.ph_registros.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    )}
    turb_dict = {r.marca_tiempo: r for r in sector.turbideces.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    )}
    hum_dict = {r.marca_tiempo: r for r in sector.humedades.filter(
        marca_tiempo__gte=fecha_inicio, marca_tiempo__lte=fecha_fin
    )}
    
    # Crear CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="sector_{sector_id}_datos.csv"'
    
    # Agregar BOM para UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Hora', 'Temperatura (°C)', 'pH', 'Turbidez (NTU)', 'Humedad (%)'])
    
    for temp in temperaturas:
        writer.writerow([
            temp.marca_tiempo.strftime('%d/%m/%Y'),
            temp.marca_tiempo.strftime('%H:%M:%S'),
            temp.valor,
            ph_dict.get(temp.marca_tiempo).valor if temp.marca_tiempo in ph_dict else '',
            turb_dict.get(temp.marca_tiempo).valor if temp.marca_tiempo in turb_dict else '',
            hum_dict.get(temp.marca_tiempo).valor if temp.marca_tiempo in hum_dict else '',
        ])
    
    return response