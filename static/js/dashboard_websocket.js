/**
 * WebSocket Client para Dashboard en tiempo real
 * 
 * Este script reemplaza el SSE (Server-Sent Events) con WebSocket
 * para recibir actualizaciones en tiempo real del cloud.
 * 
 * Uso:
 * - Incluir este script en sector_detail.html
 * - Asegurar que sectorId esté definido en el template
 */

class DashboardWebSocket {
    constructor(sectorId) {
        this.sectorId = sectorId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectInterval = 5000; // 5 segundos
        this.heartbeatInterval = null;

        // Callbacks
        this.onDataReceived = null;
        this.onConnected = null;
        this.onDisconnected = null;
        this.onError = null;

        this.connect();
    }

    /**
     * Construir URL del WebSocket
     */
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/dashboard/${this.sectorId}/`;
    }

    /**
     * Conectar al WebSocket
     */
    connect() {
        console.log(`🔌 Conectando WebSocket para sector ${this.sectorId}...`);

        const wsUrl = this.getWebSocketUrl();

        try {
            this.ws = new WebSocket(wsUrl);

            // Event: Conexión abierta
            this.ws.onopen = (event) => {
                console.log('✅ WebSocket conectado');
                this.reconnectAttempts = 0;

                // Iniciar heartbeat
                this.startHeartbeat();

                // Callback
                if (this.onConnected) {
                    this.onConnected();
                }

                // Actualizar UI
                this.updateConnectionStatus(true);
            };

            // Event: Mensaje recibido
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    console.log('📨 Mensaje recibido:', message);

                    // Manejar diferentes tipos de mensajes
                    switch (message.type) {
                        case 'connection_established':
                            console.log(`✅ ${message.message}`);
                            break;

                        case 'sensor_data':
                            // Datos de sensores
                            this.handleSensorData(message.data);
                            break;

                        default:
                            console.log('Mensaje no reconocido:', message);
                    }

                } catch (error) {
                    console.error('❌ Error parseando mensaje:', error);
                }
            };

            // Event: Error
            this.ws.onerror = (error) => {
                console.error('❌ Error en WebSocket:', error);

                // Callback
                if (this.onError) {
                    this.onError(error);
                }
            };

            // Event: Conexión cerrada
            this.ws.onclose = (event) => {
                console.log('🔌 WebSocket cerrado:', event.code, event.reason);

                // Detener heartbeat
                this.stopHeartbeat();

                // Callback
                if (this.onDisconnected) {
                    this.onDisconnected(event);
                }

                // Actualizar UI
                this.updateConnectionStatus(false);

                // Intentar reconectar
                this.reconnect();
            };

        } catch (error) {
            console.error('❌ Error creando WebSocket:', error);
            this.reconnect();
        }
    }

    /**
     * Manejar datos de sensores recibidos
     */
    handleSensorData(data) {
        console.log('📊 Datos de sensores:', data);

        // Callback personalizado
        if (this.onDataReceived) {
            this.onDataReceived(data);
        }

        // Actualizar cards
        this.updateCards(data);

        // Actualizar gráfico
        if (typeof pushDataPoint === 'function') {
            pushDataPoint(data);
        }
    }

    /**
     * Actualizar cards con nuevos valores
     */
    updateCards(datos) {
        // Temperatura
        if (datos.temperatura !== null && datos.temperatura !== undefined) {
            const tempElement = document.querySelector('[data-sensor="temperatura"]');
            if (tempElement) {
                tempElement.textContent = `${datos.temperatura.toFixed(1)}°C`;
                this.animateCard(tempElement);
            }
        }

        // pH
        if (datos.ph !== null && datos.ph !== undefined) {
            const phElement = document.querySelector('[data-sensor="ph"]');
            if (phElement) {
                phElement.textContent = datos.ph.toFixed(2);
                this.animateCard(phElement);
            }
        }

        // Turbidez
        if (datos.turbidez !== null && datos.turbidez !== undefined) {
            const turbElement = document.querySelector('[data-sensor="turbidez"]');
            if (turbElement) {
                turbElement.textContent = `${datos.turbidez.toFixed(1)} NTU`;
                this.animateCard(turbElement);
            }
        }

        // Humedad
        if (datos.humedad !== null && datos.humedad !== undefined) {
            const humElement = document.querySelector('[data-sensor="humedad"]');
            if (humElement) {
                humElement.textContent = `${datos.humedad.toFixed(1)}%`;
                this.animateCard(humElement);
            }
        }

        // Salinidad
        if (datos.salinidad !== null && datos.salinidad !== undefined) {
            const salElement = document.querySelector('[data-sensor="salinidad"]');
            if (salElement) {
                salElement.textContent = `${datos.salinidad.toFixed(1)} PSU`;
                this.animateCard(salElement);
            }
        }
    }

    /**
     * Animar card cuando se actualiza
     */
    animateCard(element) {
        element.classList.add('sensor-update');
        setTimeout(() => {
            element.classList.remove('sensor-update');
        }, 500);
    }

    /**
     * Actualizar indicador de conexión en la UI
     */
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('ws-status');
        if (indicator) {
            if (connected) {
                indicator.className = 'ws-status connected';
                indicator.innerHTML = '<i class="fa-solid fa-circle"></i> Conectado';
            } else {
                indicator.className = 'ws-status disconnected';
                indicator.innerHTML = '<i class="fa-solid fa-circle"></i> Desconectado';
            }
        }
    }

    /**
     * Intentar reconexión
     */
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Máximo de intentos de reconexión alcanzado');
            return;
        }

        this.reconnectAttempts++;
        console.log(`🔄 Reintentando conexión (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval);
    }

    /**
     * Iniciar heartbeat para mantener conexión viva
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
                console.log('💓 Heartbeat enviado');
            }
        }, 30000); // Cada 30 segundos
    }

    /**
     * Detener heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Enviar mensaje al servidor (opcional)
     */
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.warn('⚠️ WebSocket no está conectado');
        }
    }

    /**
     * Cerrar conexión manualmente
     */
    disconnect() {
        this.reconnectAttempts = this.maxReconnectAttempts; // Evitar reconexión
        if (this.ws) {
            this.ws.close();
        }
    }
}

// ============================================================================
// INICIALIZACIÓN AUTOMÁTICA
// ============================================================================

// Variable global para acceder al WebSocket desde cualquier parte
let dashboardWS = null;

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function () {
    // Solo inicializar si estamos en CLOUD
    if (typeof IS_CLOUD !== 'undefined' && IS_CLOUD) {
        console.log('🌐 Inicializando WebSocket para dashboard en CLOUD');

        // Obtener sector_id del contexto (debe estar definido en el template)
        if (typeof sectorId !== 'undefined') {
            dashboardWS = new DashboardWebSocket(sectorId);

            // Configurar callbacks (opcional)
            dashboardWS.onConnected = function () {
                console.log('✅ Callback: Conectado');
            };

            dashboardWS.onDisconnected = function (event) {
                console.log('🔌 Callback: Desconectado');
            };

            dashboardWS.onError = function (error) {
                console.error('❌ Callback: Error', error);
            };

            dashboardWS.onDataReceived = function (data) {
                console.log('📊 Callback: Datos recibidos', data);
            };
        } else {
            console.error('❌ sectorId no está definido');
        }
    } else {
        console.log('📍 Entorno LOCAL - usando SSE en lugar de WebSocket');
    }
});

// ============================================================================
// CSS para animaciones
// ============================================================================

// Inyectar estilos para animaciones
const style = document.createElement('style');
style.textContent = `
    /* Indicador de conexión WebSocket */
    .ws-status {
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        z-index: 1000;
        border: 1px solid transparent;
        display: flex;
        align-items: center;
        gap: 6px;
        background: #f5f5f5;
    }

    .ws-status i {
        font-size: 10px;
    }

    .ws-status.connected i {
        color: #3cb043;
    }

    .ws-status.disconnected i {
        color: #c62828;
    }
    
    /* Animación para cards actualizados */
    @keyframes sensor-pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    .sensor-update {
        animation: sensor-pulse 0.5s ease;
        background-color: rgba(13, 110, 253, 0.1) !important;
        transition: background-color 0.5s ease;
    }
`;
document.head.appendChild(style);

// ============================================================================
// COMPATIBILIDAD CON CÓDIGO EXISTENTE
// ============================================================================

/**
 * Si el código existente tiene funciones como leerDatos() que usan SSE,
 * podemos mantenerlas para LOCAL y usar WebSocket solo en CLOUD.
 */

// Función original para LOCAL (SSE)
function leerDatos() {
    if (typeof IS_LOCAL !== 'undefined' && IS_LOCAL) {
        // Usar SSE (código existente)
        const sectorId = typeof window.sectorId !== 'undefined' ? window.sectorId : 1;
        const eventSource = new EventSource(`/stream-sensores/?sector_id=${sectorId}`);

        eventSource.onmessage = function (event) {
            const datos = JSON.parse(event.data);

            // Actualizar cards
            if (dashboardWS) {
                dashboardWS.updateCards(datos);
            }

            // Actualizar gráfico
            if (typeof pushDataPoint === 'function') {
                pushDataPoint(datos);
            }
        };

        eventSource.onerror = function (error) {
            console.error('❌ Error en SSE:', error);
            eventSource.close();
        };
    } else {
        console.log('⚠️ leerDatos() solo funciona en LOCAL (use WebSocket en CLOUD)');
    }
}