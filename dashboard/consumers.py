"""
WebSocket Consumers para Django Channels

SensorConsumer: Recibe datos del entorno LOCAL vía WebSocket
DashboardConsumer: Envía datos a los dashboards en browsers
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.conf import settings
from datetime import datetime


class SensorConsumer(AsyncWebsocketConsumer):
    """
    Consumer que recibe datos de sensores desde el entorno LOCAL.
    
    Autenticación: Token en query string
    URL: ws://cloud.com/ws/sensores/?token=YOUR_API_KEY
    
    Flujo:
    1. Valida token en connect()
    2. Recibe datos en receive()
    3. Guarda en PostgreSQL
    4. Hace broadcast a grupo 'dashboard_{sector_id}'
    """
    
    async def connect(self):
        # Obtener token del query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        
        # Parsear query string manualmente
        if 'token=' in query_string:
            for param in query_string.split('&'):
                if param.startswith('token='):
                    token = param.split('=')[1]
                    break
        
        print(f"🔐 Token recibido: {token}")
        print(f"🔑 Token esperado: {settings.CLOUD_API_KEY}")
        
        # Validar token
        if not token or token != settings.CLOUD_API_KEY:
            print("❌ Token inválido o faltante")
            await self.close(code=4003)
            return
        
        print("✅ Token válido - Aceptando conexión")
        await self.accept()
    
    async def disconnect(self, close_code):
        """Cleanup al desconectar"""
        print(f"🔌 WebSocket LOCAL desconectado (código: {close_code})")
    
    async def receive(self, text_data):
        """
        Recibir datos del LOCAL y procesarlos.
        
        Formato esperado:
        {
            "sector_id": 1,
            "temperatura": 25.5,
            "ph": 7.2,
            "turbidez": 10.5,
            "humedad": 65.3,
            "salinidad": null,
            "marca_tiempo": "2025-01-15T10:30:00Z"
        }
        """
        try:
            data = json.loads(text_data)
            print(f"📊 Datos recibidos del LOCAL: {data}")
            
            # Validar datos requeridos
            if 'sector_id' not in data:
                await self.send(text_data=json.dumps({
                    'error': 'Falta sector_id'
                }))
                return
            
            sector_id = data.get('sector_id')
            
            # Guardar en base de datos
            guardado = await self.guardar_lecturas(data)
            
            if guardado:
                print(f"💾 Lecturas guardadas en PostgreSQL")
                
                # Hacer broadcast a todos los dashboards conectados a este sector
                await self.channel_layer.group_send(
                    f'dashboard_{sector_id}',
                    {
                        'type': 'sensor_update',
                        'data': data
                    }
                )
                print(f"📡 Broadcast enviado a dashboard_{sector_id}")
                
                # Confirmar al LOCAL
                await self.send(text_data=json.dumps({
                    'status': 'success',
                    'mensaje': 'Datos guardados y broadcast realizado'
                }))
            else:
                await self.send(text_data=json.dumps({
                    'status': 'error',
                    'mensaje': 'Error al guardar datos'
                }))
                
        except json.JSONDecodeError as e:
            print(f"❌ Error JSON: {e}")
            await self.send(text_data=json.dumps({
                'error': f'JSON inválido: {str(e)}'
            }))
        except Exception as e:
            print(f"❌ Error procesando datos: {e}")
            await self.send(text_data=json.dumps({
                'error': f'Error: {str(e)}'
            }))
    
    @database_sync_to_async
    def guardar_lecturas(self, datos):
        """
        Guardar lecturas en PostgreSQL (async wrapper)
        
        Returns:
            bool: True si se guardó correctamente
        """
        try:
            from dashboard.models import (
                Sector, HistorialTemperatura, HistorialSalinidad,
                HistorialPh, HistorialTurbidez, HistorialHumedad
            )
            
            sector_id = datos.get('sector_id')
            sector = Sector.objects.get(id=sector_id)
            
            # Parsear timestamp (si viene del LOCAL) o usar actual
            marca_tiempo_str = datos.get('marca_tiempo')
            if marca_tiempo_str:
                # Intentar parsear ISO format
                try:
                    marca_tiempo = datetime.fromisoformat(marca_tiempo_str.replace('Z', '+00:00'))
                    if timezone.is_naive(marca_tiempo):
                        marca_tiempo = timezone.make_aware(marca_tiempo)
                except:
                    marca_tiempo = timezone.now()
            else:
                marca_tiempo = timezone.now()
            
            guardados = 0
            
            # Guardar temperatura
            if datos.get('temperatura') is not None and datos['temperatura'] != -999:
                HistorialTemperatura.objects.create(
                    sector=sector,
                    valor=datos['temperatura'],
                    marca_tiempo=marca_tiempo
                )
                guardados += 1
            
            # Guardar pH
            if datos.get('ph') is not None:
                HistorialPh.objects.create(
                    sector=sector,
                    valor=datos['ph'],
                    marca_tiempo=marca_tiempo
                )
                guardados += 1
            
            # Guardar turbidez
            if datos.get('turbidez') is not None:
                HistorialTurbidez.objects.create(
                    sector=sector,
                    valor=datos['turbidez'],
                    marca_tiempo=marca_tiempo
                )
                guardados += 1
            
            # Guardar humedad
            if datos.get('humedad') is not None:
                HistorialHumedad.objects.create(
                    sector=sector,
                    valor=datos['humedad'],
                    marca_tiempo=marca_tiempo
                )
                guardados += 1
            
            # Guardar salinidad
            if datos.get('salinidad') is not None:
                HistorialSalinidad.objects.create(
                    sector=sector,
                    valor=datos['salinidad'],
                    marca_tiempo=marca_tiempo
                )
                guardados += 1
            
            print(f"💾 {guardados} lecturas guardadas en PostgreSQL")
            return True
            
        except Sector.DoesNotExist:
            print(f"❌ Sector {sector_id} no existe en cloud")
            return False
        except Exception as e:
            print(f"❌ Error al guardar en PostgreSQL: {e}")
            import traceback
            traceback.print_exc()
            return False


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    Consumer que envía datos en tiempo real a los dashboards (browsers).
    
    Autenticación: Session de Django (usuario logueado)
    URL: ws://cloud.com/ws/dashboard/1/
    
    Flujo:
    1. Usuario debe estar autenticado (Django session)
    2. Se une al grupo 'dashboard_{sector_id}'
    3. Recibe broadcasts de SensorConsumer
    4. Envía datos al browser
    """
    
    async def connect(self):
        """Validar autenticación y unirse al grupo"""
        
        # Obtener sector_id de la URL
        self.sector_id = self.scope['url_route']['kwargs']['sector_id']
        self.group_name = f'dashboard_{self.sector_id}'
        
        # Verificar autenticación (si el usuario está logueado)
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            print(f"❌ Usuario no autenticado intentó conectarse al dashboard")
            await self.close(code=4003)
            return
        
        # Unirse al grupo del sector
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        print(f"✅ Dashboard WebSocket conectado para sector {self.sector_id} (usuario: {user.username})")
        await self.accept()
        
        # Enviar mensaje de bienvenida
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Conectado al sector {self.sector_id}',
            'sector_id': self.sector_id
        }))
    
    async def disconnect(self, close_code):
        """Salir del grupo al desconectar"""
        
        # Salir del grupo
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        print(f"🔌 Dashboard WebSocket desconectado para sector {self.sector_id} (código: {close_code})")
    
    async def receive(self, text_data):
        """
        Opcional: Manejar mensajes del browser (por si quieres comandos bidireccionales)
        """
        try:
            data = json.loads(text_data)
            print(f"📨 Mensaje del dashboard: {data}")
            
            # Aquí podrías implementar comandos como:
            # - "ping" para keep-alive
            # - "request_history" para pedir datos históricos
            # etc.
            
        except Exception as e:
            print(f"❌ Error procesando mensaje del dashboard: {e}")
    
    async def sensor_update(self, event):
        """
        Manejador para broadcast de SensorConsumer.
        Este método se llama cuando SensorConsumer hace group_send.
        
        El nombre 'sensor_update' debe coincidir con el 'type' en group_send.
        """
        data = event['data']
        
        # Enviar datos al browser
        await self.send(text_data=json.dumps({
            'type': 'sensor_data',
            'data': data
        }))
        
        print(f"📤 Datos enviados al dashboard: {data}")