
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
def iniciar_lectura_sensores(request):
    global lectura_activa
    lectura_activa = True
    
    if not conectar_arduino():
        return JsonResponse({
            'error': 'No se pudo conectar con Arduino en COM3'
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
            
            time.sleep(2)
        
        yield "data: {\"status\": \"cerrado\"}\n\n"
    
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response