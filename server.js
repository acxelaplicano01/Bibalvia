#!/usr/bin/env node
/*
  Serial → WebSocket bridge para el dashboard
  - Auto-detecta puerto serie o usa SERIAL_PORT env / --serial
  - Expone WS en ws://localhost:8080 (puerto configurable)
  - Sirve archivos estáticos (dashboard.html) desde la carpeta del proyecto

  Uso:
    node server.js --ws-port 8080 --http-port 8080 --serial COM3
    o establecer SERIAL_PORT=COM3 y ejecutar sin --serial

  Requiere: serialport, express, ws
    npm install
    npm install serialport express ws
*/

const { SerialPort } = require('serialport');
const express = require('express');
const { WebSocketServer } = require('ws');
const path = require('path');

const argv = require('minimist')(process.argv.slice(2));
const WS_PORT = argv['ws-port'] || argv['w'] || 8080;
const HTTP_PORT = argv['http-port'] || argv['http'] || WS_PORT;
const SERIAL_ARG = argv.serial || process.env.SERIAL_PORT || null;

async function pickSerialPort(preferred) {
  try {
    const ports = await SerialPort.list();
    if (preferred) {
      const found = ports.find(p => p.path === preferred || p.path.endsWith(preferred));
      if (found) return found.path;
    }
    // Intenta encontrar puertos que suelan ser Arduinos
    const arduinoPort = ports.find(p => p.manufacturer && (p.manufacturer.includes('Arduino') || p.manufacturer.includes('FTDI')));
    if (arduinoPort) return arduinoPort.path;
    if (ports.length === 0) return null;
    return ports[0].path; // Toma el primer puerto si no encuentra el preferido ni un Arduino
  } catch (e) {
    console.error('Error listando puertos serie:', e);
    return null;
  }
}

async function start() {
  const staticDir = path.resolve(__dirname);
  const app = express();
  app.use(express.static(staticDir));

  const server = app.listen(HTTP_PORT, () => {
    console.log(`HTTP server sirviendo ${staticDir} en http://localhost:${HTTP_PORT}`);
  });

  const wss = new WebSocketServer({ server });
  
  // Función para retransmitir datos a todos los clientes WS conectados
  function broadcast(data) {
    wss.clients.forEach(client => {
      if (client.readyState === 1) { // 1 = OPEN
        client.send(data);
      }
    });
  }

  wss.on('connection', ws => {
    console.log('Cliente WS conectado');
    // Si tienes que enviar estado inicial o comandos a Arduino (no es el caso aquí)
  });

  const portPath = await pickSerialPort(SERIAL_ARG);
  if (!portPath) {
    console.warn('No se detectó puerto serie. Ejecutando en modo simulación (fallback) para el dashboard.');
    return;
  }

  console.log('🔌 Conectando a puerto serie:', portPath, 'a 9600 baudios...');
  const sp = new SerialPort({ path: portPath, baudRate: 9600 });
  let buffer = '';
  
  sp.on('data', chunk => {
    buffer += chunk.toString();
    let idx;
    
    // Procesa el buffer línea por línea (terminado por \n)
    while ((idx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (!line) continue;
      
      // La línea debe ser un objeto JSON de Arduino: {"tempC":25.1,"turbidez":50,"salinidad":55,"vivo":"true","clasif":"MEJILLON"}
      try {
        const sensorData = JSON.parse(line);
        // Construye el mensaje que espera el dashboard JS
        const wsMessage = JSON.stringify({
          type: 'sensor',
          data: sensorData,
          ts: Date.now()
        });
        
        // 1. Envía el JSON limpio al dashboard
        broadcast(wsMessage);
        
        // 2. Muestra un log en la consola del servidor
        console.log(`[${new Date().toLocaleTimeString()}] Data:`, sensorData.tempC, sensorData.clasif);
        
      } catch (e) {
        // Si no es JSON, envíalo como texto de log
        broadcast(JSON.stringify({ type: 'text', data: line }));
        console.error('JSON parse error, data raw:', line);
      }
    }
  });

  sp.on('open', () => console.log('Puerto serie abierto. Datos de Arduino listos para WS.'));
  sp.on('error', err => console.error('Error en el puerto serie:', err.message));
}

start();