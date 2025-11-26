"""
WebSocket URL routing para Django Channels
Define las rutas de WebSocket similares a urls.py
"""

from django.urls import re_path
from dashboard import consumers

websocket_urlpatterns = [
    # WebSocket para recibir datos de sensores desde LOCAL
    # URL: ws://localhost:8000/ws/sensores/?token=YOUR_API_KEY
    re_path(r'ws/sensores/$', consumers.SensorConsumer.as_asgi()),
    
    # WebSocket para enviar datos al dashboard (browser)
    # URL: ws://localhost:8000/ws/dashboard/1/
    re_path(r'ws/dashboard/(?P<sector_id>\d+)/$', consumers.DashboardConsumer.as_asgi()),
]