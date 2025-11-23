import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bivalvia.settings')
django.setup()

from dashboard.views import enviar_a_nube
from datetime import datetime

# Datos simulados como si vinieran del Arduino
datos_simulados = {
    'temperatura': 24.5,
    'ph': 7.2,
    'turbidez': 50.0,
    'humedad': 80.5
}

sector_id = 1  # Asegúrate de que este sector exista en la nube

print("🧪 Probando envío a la nube...")
print(f"📊 Datos a enviar: {datos_simulados}")
print(f"🎯 Sector ID: {sector_id}")
print("-" * 50)

resultado = enviar_a_nube(datos_simulados, sector_id)

if resultado:
    print("\n✅ ¡Prueba exitosa! Los datos se enviaron correctamente.")
else:
    print("\n❌ La prueba falló. Revisa los mensajes de error arriba.")