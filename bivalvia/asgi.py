"""
ASGI config for bivalvia project.

Expone la aplicación ASGI como una variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, ver:
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

# Importante: establecer settings ANTES de importar Channels
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bivalvia.settings')

# Inicializar Django ASGI application temprano para asegurar el AppRegistry
# esté poblado antes de importar código que pueda importar modelos ORM.
django_asgi_app = get_asgi_application()

# Ahora sí importar Channels y routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from bivalvia import routing

application = ProtocolTypeRouter({
    # Django's ASGI application para manejar HTTP tradicional
    "http": django_asgi_app,
    
    # WebSocket handler
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})