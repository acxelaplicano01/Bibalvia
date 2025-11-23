import os
import django
import random
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bivalvia.settings')
django.setup()

from dashboard.views import guardar_lectura_local, enviar_a_nube
from django.conf import settings

def generar_datos_realistas():
    """Genera datos simulados realistas"""
    return {
        'temperatura': round(random.uniform(20.0, 30.0), 2),
        'ph': round(random.uniform(6.5, 8.5), 2),
        'turbidez': round(random.uniform(30.0, 100.0), 0),
        'humedad': round(random.uniform(60.0, 95.0), 2)
    }

print("🤖 SIMULADOR DE ARDUINO")
print("=" * 60)
print(f"Entorno: {settings.ENVIRONMENT.upper()}")
print(f"Base de datos: {'SQLite' if settings.IS_LOCAL else 'PostgreSQL'}")

# Obtener sector_id
sector_id = input("\n🎯 Ingresa el ID del sector a monitorear (default: 1): ").strip()
sector_id = sector_id if sector_id else "1"

# Validar que el sector existe
from dashboard.models import Sector
try:
    sector = Sector.objects.get(id=sector_id)
    print(f"✓ Sector encontrado: {sector.nombre_sector or f'Sector {sector.id}'}")
except Sector.DoesNotExist:
    print(f"❌ ERROR: Sector {sector_id} no existe")
    print("\nCrea el sector primero desde la interfaz web")
    exit(1)

print("\n📡 Enviando datos cada 5 segundos...")
print("🛑 Presiona Ctrl+C para detener\n")
print("-" * 60)

try:
    contador = 1
    while True:
        datos = generar_datos_realistas()
        
        print(f"\n📊 Lectura #{contador} - {time.strftime('%H:%M:%S')}")
        print(f"   🌡️  Temperatura: {datos['temperatura']}°C")
        print(f"   🧪 pH: {datos['ph']}")
        print(f"   💧 Turbidez: {datos['turbidez']} NTU")
        print(f"   💨 Humedad: {datos['humedad']}%")
        
        # Guardar localmente
        print(f"   💾 Guardando en base de datos local...", end=" ")
        if guardar_lectura_local(datos, sector_id):
            print("✅")
        else:
            print("❌")
        
        # Enviar a la nube si estamos en LOCAL
        if settings.IS_LOCAL:
            print(f"   ☁️  Enviando a la nube...", end=" ")
            if enviar_a_nube(datos, sector_id):
                print("✅")
            else:
                print("❌")
        
        contador += 1
        time.sleep(5)
        
except KeyboardInterrupt:
    print("\n\n🛑 Simulación detenida")
    print(f"📈 Total de lecturas: {contador - 1}")
    print("\n✅ Puedes verificar los datos en:")
    print(f"   LOCAL: http://localhost:8000/sector/{sector_id}/")
    if settings.IS_LOCAL:
        print(f"   CLOUD: https://bivalvia-cloud.onrender.com/sector/{sector_id}/")