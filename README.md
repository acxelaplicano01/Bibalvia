# Bibalvia — Dashboard IoT

Interfaz web para visualizar sensores de un proyecto IoT con Arduino (Tinkercad/real).

Archivos principales:
- `dashboard.html` — Interfaz responsiva (Bootstrap + Chart.js). Incluye simulador y ejemplos de integración WebSocket/REST.
- `server.js` — Puente opcional Serial → WebSocket que lee datos JSON desde el puerto serie del Arduino y los reenvía a clientes WebSocket. También sirve archivos estáticos.
- `package.json` — dependencias del puente.

Cómo probar localmente (puente serial):

1. Coloca la imagen de la simulación en `assets/Terrific Stantia.png` si quieres que se muestre.
2. Instala dependencias:

```powershell
npm install
```

3. Conecta tu Arduino al puerto USB. Puedes pasar el puerto con `--serial COM3` o establecer la variable de entorno `SERIAL_PORT`.

4. Ejecuta el servidor:

```powershell
node server.js --http-port 8080 --serial COM3
```

5. Abre en el navegador: `http://localhost:8080/dashboard.html` (o simplemente `http://localhost:8080` si `dashboard.html` está en la raíz).

Integración alternativa (sin puente):
- Puedes adaptar `dashboard.html` para consultar una API REST (`pollREST`) o para conectarse directamente a un WebSocket que provea los mismos JSONs.

Formato que el Arduino envía por Serial (ejemplo que ya existe en tu sketch):
```json
{"tempC":25.1,"turbidez":48,"salinidad":62,"vivo":true,"clasif":"MEJILLON"}
```

Siguientes mejoras sugeridas:
- Añadir autenticación simple al WS/HTTP si el proyecto será accesible fuera de la LAN.
- Guardar datos históricos en un archivo o base de datos ligera (SQLite) y mostrar rangos de tiempo.
- Añadir alertas por email/Telegram cuando `salinidad` o `tempC` excedan umbrales.
# Bibalvia