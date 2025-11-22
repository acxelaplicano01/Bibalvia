import requests
from datetime import datetime
from decouple import config

CLOUD_API_URL = config('CLOUD_API_URL')
CLOUD_API_KEY = config('CLOUD_API_KEY')

payload = {
    'sector_id': 1,  # Cambia por un sector que exista en la nube
    'temperatura': 24.5,
    'salinidad': None,
    'ph': 7.2,
    'turbidez': 50.0,
    'humedad': 80.0,
    'marca_tiempo': datetime.now().isoformat()
}

headers = {
    'X-API-Key': CLOUD_API_KEY,
    'Content-Type': 'application/json'
}

try:
    response = requests.post(
        f"{CLOUD_API_URL}/lectura/",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
except Exception as e:
    print(f"Error: {e}")