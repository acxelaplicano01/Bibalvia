import os
import django
import random
import time
import asyncio
from django.utils import timezone
from asgiref.sync import sync_to_async

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bivalvia.settings')
django.setup()

from dashboard.views import guardar_lectura_local
from dashboard.ws_client import sensor_ws_client, enviar_a_nube_ws
from django.conf import settings
from dashboard.models import Sector

def generar_datos_realistas():
    return {
        'temperatura': round(random.uniform(20.0, 30.0), 2),
        'ph': round(random.uniform(6.5, 8.5), 2),
        'turbidez': round(random.uniform(30.0, 100.0), 0),
        'humedad': round(random.uniform(60.0, 95.0), 2)
    }

@sync_to_async
def get_sector(sector_id):
    return Sector.objects.get(id=sector_id)

@sync_to_async
def guardar_local(datos, sector_id, marca_tiempo):
    return guardar_lectura_local(datos, sector_id, marca_tiempo)

async def simular():
    print("🤖 SIMULADOR DE ARDUINO CON WEBSOCKET")
    print("=" * 60)
    
    sector_id = input("\n🎯 ID del sector (default: 1): ").strip() or "1"
    
    try:
        sector = await get_sector(sector_id)
        print(f"✓ Sector: {sector.nombre_sector or f'Sector {sector.id}'}")
    except Sector.DoesNotExist:
        print(f"❌ Sector {sector_id} no existe")
        return
    
    if settings.IS_LOCAL:
        print("\n🔌 Conectando WebSocket...")
        if await sensor_ws_client.connect():
            print("✅ Conectado")
        else:
            print("❌ Error")
            return
    
    print("\n📡 Enviando datos cada 5s (Ctrl+C para detener)\n")
    
    try:
        contador = 1
        while True:
            datos = generar_datos_realistas()
            marca_tiempo = timezone.now()
            
            print(f"\n📊 #{contador} - {time.strftime('%H:%M:%S')}")
            print(f"   Temp: {datos['temperatura']}°C | pH: {datos['ph']}")
            print(f"   Turb: {datos['turbidez']} | Hum: {datos['humedad']}%")
            
            print(f"   💾 Local...", end=" ")
            if await guardar_local(datos, sector_id, marca_tiempo):
                print("✅")
            else:
                print("❌")
            
            if settings.IS_LOCAL:
                print(f"   ☁️  Cloud...", end=" ")
                if await enviar_a_nube_ws(datos, sector_id, marca_tiempo):
                    print("✅")
                else:
                    print("❌")
            
            contador += 1
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Detenido")
        if settings.IS_LOCAL:
            await sensor_ws_client.disconnect()
        print(f"Total: {contador - 1} lecturas")

if __name__ == "__main__":
    asyncio.run(simular())