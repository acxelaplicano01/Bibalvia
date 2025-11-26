"""
Django settings for bivalvia project.

ACTUALIZADO para soportar Django Channels y WebSockets.
"""

import os
import dj_database_url
from pathlib import Path
from decouple import config

LOGIN_URL = '/'

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Leer ALLOWED_HOSTS
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Configuración de entorno
ENVIRONMENT = config('ENVIRONMENT', default='local')
IS_LOCAL = ENVIRONMENT == 'local'
IS_CLOUD = ENVIRONMENT == 'cloud'

# Application definition
INSTALLED_APPS = [
    # Django Channels debe ir ANTES de django.contrib.staticfiles
    'daphne',  # ← NUEVO: Servidor ASGI para WebSockets
    
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Apps de terceros
    'channels',  # ← NUEVO: Django Channels
    'rest_framework',
    
    # Apps propias
    'dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Para servir archivos estáticos
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bivalvia.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context_processors.environment',
            ],
        },
    },
]

# ============================================================================
# ASGI/WSGI CONFIGURATION
# ============================================================================

# Para desarrollo local o cuando no usas WebSockets
WSGI_APPLICATION = 'bivalvia.wsgi.application'

# Para producción con WebSockets (IMPORTANTE: Render debe usar esto)
ASGI_APPLICATION = 'bivalvia.asgi.application'

# ============================================================================
# CHANNELS CONFIGURATION
# ============================================================================

if IS_CLOUD:
    # En producción (Render): usar Redis como channel layer
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [config('REDIS_URL', default='redis://localhost:6379')],
            },
        },
    }
else:
    # En desarrollo local: usar InMemoryChannelLayer (solo para testing)
    # NOTA: InMemory NO funciona en producción con múltiples workers
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer'
        }
    }

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,  # Mantener conexiones abiertas para rendimiento
    )
}

# ============================================================================
# API CONFIGURATION (para backward compatibility con REST)
# ============================================================================

CLOUD_API_URL = config('CLOUD_API_URL', default='')
CLOUD_API_KEY = config('CLOUD_API_KEY', default='')

# ============================================================================
# WEBSOCKET CONFIGURATION (nuevo)
# ============================================================================

if IS_LOCAL:
    # URL del WebSocket en el cloud (desde el local)
    CLOUD_WS_URL = config(
        'CLOUD_WS_URL',
        default='ws://localhost:8000/ws/sensores/'  # Para testing
    )
else:
    # En cloud no necesitamos esta variable
    CLOUD_WS_URL = None

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATICFILES_DIRS = [BASE_DIR / "static"]

# ============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# SECURITY SETTINGS (solo para producción)
# ============================================================================

if not DEBUG:
    # HTTPS enforcement
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HSTS
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ============================================================================
# LOGGING (opcional pero útil)
# ============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'channels': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}