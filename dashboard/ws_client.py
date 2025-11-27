"""
Cliente WebSocket para enviar datos de sensores del LOCAL al CLOUD.

Este módulo reemplaza la función enviar_a_nube() que usaba REST.

Características:
- Conexión persistente
- Reconexión automática
- Manejo de errores
- Heartbeat para mantener conexión viva

Uso:
    from ws_client import sensor_ws_client
    
    # Enviar datos
    await sensor_ws_client.send_sensor_data({
        'sector_id': 1,
        'temperatura': 25.5,
        'ph': 7.2,
        ...
    })
"""

import asyncio
import websockets
import json
import logging
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class SensorWebSocketClient:
    """
    Cliente WebSocket para enviar datos de sensores al cloud.
    
    Maneja conexión persistente con reconexión automática.
    """
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.url: str = self._build_url()
        
        self.connected: bool = False
        self.reconnect_interval: int = 5  # segundos
        self.max_reconnect_attempts: int = 10
        self.heartbeat_interval: int = 30  # segundos
        
        # Task para mantener la conexión
        self.connection_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    def _build_url(self) -> str:
        # Obtener URL del WebSocket
        cloud_url = settings.CLOUD_WS_URL
        
        # Si ya viene completa, usarla directamente
        if cloud_url and '/ws/sensores/' in cloud_url:
            ws_url = cloud_url
        else:
            # Construir desde API_URL
            cloud_url = settings.CLOUD_API_URL or ''
            if cloud_url.startswith('https://'):
                ws_url = cloud_url.replace('https://', 'wss://')
            elif cloud_url.startswith('http://'):
                ws_url = cloud_url.replace('http://', 'ws://')
            else:
                ws_url = cloud_url
            
            if not ws_url.endswith('/'):
                ws_url += '/'
            ws_url += 'ws/sensores/'
        
        # Agregar token
        api_key = settings.CLOUD_API_KEY
        full_url = f"{ws_url}?token={api_key}"
        
        return full_url
    
    async def connect(self) -> bool:
        """
        Establecer conexión WebSocket con el cloud.
        
        Returns:
            bool: True si la conexión fue exitosa
        """
        try:
            logger.info(f"🔌 Intentando conectar a: {self.url.split('?')[0]}...")
            
            self.websocket = await websockets.connect(
                self.url,
                ping_interval=20,  # Enviar ping cada 20s
                ping_timeout=10,   # Timeout de pong
                close_timeout=10   # Timeout para cerrar
            )
            
            self.connected = True
            logger.info("✅ WebSocket conectado al cloud")
            
            # Iniciar heartbeat
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            
            return True
            
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 4001:
                logger.error("❌ Token de autenticación inválido")
            else:
                logger.error(f"❌ Error de conexión: {e.status_code}")
            self.connected = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al conectar WebSocket: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Cerrar conexión WebSocket de forma limpia"""
        
        self.connected = False
        
        # Cancelar heartbeat
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
        
        # Cerrar websocket
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 WebSocket desconectado limpiamente")
            except Exception as e:
                logger.error(f"Error al cerrar WebSocket: {e}")
            finally:
                self.websocket = None
    
    async def _heartbeat_loop(self):
        """Mantener la conexión viva con heartbeats periódicos"""
        
        while self.connected and self.websocket:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.websocket and not self.websocket.closed:
                    # Enviar ping
                    pong = await self.websocket.ping()
                    await asyncio.wait_for(pong, timeout=10)
                    logger.debug("💓 Heartbeat enviado")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"❌ Error en heartbeat: {e}")
                self.connected = False
                break
    
    async def send_sensor_data(self, data: Dict[str, Any]) -> bool:
        """
        Enviar datos de sensores al cloud.
        
        Args:
            data: Diccionario con los datos del sensor
                {
                    'sector_id': int,
                    'temperatura': float,
                    'ph': float,
                    'turbidez': float,
                    'humedad': float,
                    'salinidad': float,
                    'marca_tiempo': str (ISO format)
                }
        
        Returns:
            bool: True si se envió correctamente
        """
        
        # Verificar conexión
        if not self.connected or not self.websocket:
            logger.warning("⚠️ No hay conexión WebSocket, intentando reconectar...")
            success = await self.connect()
            if not success:
                logger.error("❌ No se pudo establecer conexión")
                return False
        
        try:
            # Convertir a JSON
            json_data = json.dumps(data)
            
            # Enviar datos
            await self.websocket.send(json_data)
            logger.info(f"📤 Datos enviados al cloud: sector={data.get('sector_id')}")
            
            # Esperar confirmación (opcional, con timeout)
            try:
                response = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=5.0
                )
                response_data = json.loads(response)
                
                if response_data.get('status') == 'success':
                    logger.info("✅ Cloud confirmó recepción")
                    return True
                else:
                    logger.warning(f"⚠️ Cloud respondió: {response_data}")
                    return True  # Aún así retornar True porque se envió
                    
            except asyncio.TimeoutError:
                logger.warning("⏱️ Timeout esperando confirmación (datos probablemente recibidos)")
                return True
            
        except websockets.exceptions.ConnectionClosed:
            logger.error("❌ Conexión cerrada al enviar datos")
            self.connected = False
            return False
            
        except Exception as e:
            logger.error(f"❌ Error al enviar datos: {e}")
            return False
    
    async def maintain_connection(self):
        """
        Mantener la conexión activa con reconexión automática.
        
        Este método debe ejecutarse en un bucle de eventos separado.
        """
        
        attempt = 0
        
        while attempt < self.max_reconnect_attempts:
            if not self.connected:
                logger.info(f"🔄 Intento de reconexión {attempt + 1}/{self.max_reconnect_attempts}")
                
                success = await self.connect()
                
                if success:
                    attempt = 0  # Resetear contador
                    logger.info("✅ Reconexión exitosa")
                else:
                    attempt += 1
                    await asyncio.sleep(self.reconnect_interval)
            else:
                # Conexión activa, esperar un poco
                await asyncio.sleep(1)
        
        logger.error(f"❌ Máximo de intentos de reconexión alcanzado")
    
    def start_background_task(self):
        """
        Iniciar tarea en background para mantener conexión.
        
        Llamar esto al iniciar la aplicación LOCAL.
        """
        if not self.connection_task or self.connection_task.done():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.connection_task = loop.create_task(self.maintain_connection())


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Instancia global del cliente (usar esta en tu código)
sensor_ws_client = SensorWebSocketClient()


# ============================================================================
# HELPER FUNCTIONS (compatibilidad con código existente)
# ============================================================================

async def enviar_a_nube_ws(datos: Dict[str, Any], sector_id: int, marca_tiempo=None) -> bool:
    """
    Función auxiliar para mantener compatibilidad con código existente.
    
    Reemplaza la función enviar_a_nube() que usaba REST.
    
    Args:
        datos: Diccionario con los datos de sensores
        sector_id: ID del sector
        marca_tiempo: Timestamp (datetime o string ISO)
    
    Returns:
        bool: True si se envió correctamente
    """
    from django.utils import timezone
    
    # Preparar timestamp
    if marca_tiempo is None:
        marca_tiempo = timezone.now()
    
    # Convertir a ISO string si es datetime
    if hasattr(marca_tiempo, 'isoformat'):
        marca_tiempo_str = marca_tiempo.isoformat()
    else:
        marca_tiempo_str = str(marca_tiempo)
    
    # Construir payload
    payload = {
        'sector_id': int(sector_id),
        'temperatura': float(datos.get('temperatura')) if datos.get('temperatura') is not None else None,
        'salinidad': float(datos.get('salinidad')) if datos.get('salinidad') is not None else None,
        'ph': float(datos.get('ph')) if datos.get('ph') is not None else None,
        'turbidez': float(datos.get('turbidez')) if datos.get('turbidez') is not None else None,
        'humedad': float(datos.get('humedad')) if datos.get('humedad') is not None else None,
        'marca_tiempo': marca_tiempo_str
    }
    
    # Enviar vía WebSocket
    return await sensor_ws_client.send_sensor_data(payload)


# ============================================================================
# SYNC WRAPPER (para usar en código síncrono)
# ============================================================================

def enviar_a_nube_ws_sync(datos: Dict[str, Any], sector_id: int, marca_tiempo=None) -> bool:
    """
    Wrapper síncrono para usar en código que no es async.
    
    NOTA: Esto crea un nuevo event loop cada vez, lo cual no es ideal.
    Para mejor performance, usa la versión async directamente.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            enviar_a_nube_ws(datos, sector_id, marca_tiempo)
        )
        loop.close()
        return result
    except Exception as e:
        logger.error(f"❌ Error en enviar_a_nube_ws_sync: {e}")
        return False