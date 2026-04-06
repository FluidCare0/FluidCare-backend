import os
import json
from pathlib import Path
from datetime import timedelta
import uuid
from decouple import config

# --------------------------
# Base Directory
# --------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------
# Security Settings
# --------------------------
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS', 
    default='127.0.0.1,localhost', 
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# --------------------------
# CORS & CSRF
# --------------------------
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS', 
    default='', 
    cast=lambda v: [s.strip() for s in v.split(',')] if v else []
)

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS', 
    default='', 
    cast=lambda v: [s.strip() for s in v.split(',')] if v else []
)

SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = False

# --------------------------
# Apps
# --------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',
    
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_ratelimit',
    'django_celery_results',
    'django_celery_beat',
    'drf_yasg',
    'channels',

    # Custom apps
    'auth_app',
    'sensor_app.apps.SensorAppConfig',
    'hospital_app',
    'survey_app',
    'notification_app',

]

# --------------------------
# Middleware
# --------------------------
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

# --------------------------
# Templates
# --------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

ASGI_APPLICATION = 'core.asgi.application'

# --------------------------
# Database
# --------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST', default='localhost'),
#         'PORT': config('DB_PORT', default=5432, cast=int),
#     }
# }

# --------------------------
# Password validation
# --------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# --------------------------
# Internationalization
# --------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --------------------------
# Static files
# --------------------------
STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --------------------------
# Auth & REST Framework
# --------------------------
AUTH_USER_MODEL = 'auth_app.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME_MINUTES', default=5, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': config('ROTATE_REFRESH_TOKENS', default=True, cast=bool),
    'BLACKLIST_AFTER_ROTATION': config('BLACKLIST_AFTER_ROTATION', default=True, cast=bool),
    'UPDATE_LAST_LOGIN': config('UPDATE_LAST_LOGIN', default=True, cast=bool),

    'ALGORITHM': config('JWT_ALGORITHM', default='HS256'),
    'SIGNING_KEY': config('SECRET_KEY'),
    'AUTH_HEADER_TYPES': (config('JWT_AUTH_HEADER_TYPE', default='Bearer'),),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# --------------------------
# Logging
# --------------------------
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },

    "handlers": {
        # --- Django Server ---
        "django_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "django.log"),
            "formatter": "verbose",
        },

        # --- Celery ---
        "celery_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "celery.log"),
            "formatter": "verbose",
        },

        # --- Channels ---
        "channels_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "channels.log"),
            "formatter": "verbose",
        },

        # --- Console (optional) ---
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },

        "mqtt_file": {
            "class": "logging.FileHandler",
            "filename": os.path.join(LOG_DIR, "mqtt.log"),
            "formatter": "verbose",
        },
    },

    "loggers": {
        # Django server logger
        "django": {
            "handlers": ["django_file", "console"],
            "level": "INFO",
            "propagate": True,
        },

        # Celery specific logger
        "celery": {
            "handlers": ["celery_file", "console"],
            "level": "INFO",
            "propagate": False,
        },

        # Channels specific logger
        "channels": {
            "handlers": ["channels_file", "console"],
            "level": "INFO",
            "propagate": False,
        },
        # ✅ New: MQTT logger
        "mqtt": {
            "handlers": ["mqtt_file", "console"],
            "level": "INFO",
            "propagate": False,
        },

        # Root logger (optional catch-all)
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}

# --------------------------
# Caches / Redis
# --------------------------
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

REDIS_URL = config('REDIS_URL', default='')

# --------------------------
# Channels
# --------------------------
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# --------------------------
# Twilio
# --------------------------
TWILIO_ACCOUNT_SID = config('TWILIO_ACCOUNT_SID', default='')
TWILIO_AUTH_TOKEN = config('TWILIO_AUTH_TOKEN', default='')
TWILIO_FROM_NUMBER = config('TWILIO_PHONE_NUMBER', default='')

# --------------------------
# Master OTP Bypass (dev/staging only)
# --------------------------
# These are ignored in production because the bypass gate checks DEBUG=False.
MASTER_PHONE = config('MASTER_PHONE', default='')
MASTER_OTP = config('MASTER_OTP', default='')

# --------------------------
# MQTT Client
# --------------------------
MQTT_BROKER = "1e578bacd37e4198a99e7a4a28756c6e.s1.eu.hivemq.cloud"
MQTT_CLIENT_ID = f"django-backend-{uuid.uuid4().hex[:6]}"
MQTT_USERNAME = "kanbs"    # leave empty for public broker
MQTT_PASSWORD = "Kartik@3165" 
MQTT_PORT = 8883
MQTT_TOPIC = 'be_project/#'

# ====== MQTT Topics (add to your existing settings) ======

# Backend → Master → Node  (master subscribes to this)
MQTT_TOPIC_MASTER_IN = 'be_project/master/in'

# Master → Backend  (backend subscribes to these)
MQTT_TOPIC_NODE_REGISTER = 'be_project/node/register'          # Code 200
MQTT_TOPIC_NODE_CONFIRM_ID = 'be_project/node/confirm_id'      # Code 202
MQTT_TOPIC_NODE_DATA = 'be_project/node/data'                   # Code 203
MQTT_TOPIC_NODE_TASK_COMPLETE = 'be_project/node/task_complete' # Code 204
MQTT_TOPIC_NODE_ERASE_CONFIRM = 'be_project/node/erase_confirm' # Code 206
MQTT_TOPIC_DISCONNECT = 'be_project/disconnect'                 # Existing

# Keep your existing MQTT_BROKER, MQTT_PORT, MQTT_CLIENT_ID, etc.

# # --------------------------
# # Email
# # --------------------------
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
# EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
# EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
# EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
# EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@yourdomain.com')

# # --------------------------
# # Firebase & reCAPTCHA
# # --------------------------
# FIREBASE_CREDENTIALS_PATH = config('FIREBASE_CREDENTIALS_PATH', default='config/firebase-service-account.json')
# RECAPTCHA_SECRET_KEY = config('RECAPTCHA_SECRET_KEY', default='')

# # --------------------------
# # Meta details
# # --------------------------
# META_APP_ID=''
# META_APP_SECRET=''
# META_REDIRECT_URL=''
# META_VERIFICATION_TOKEN='12345'


# # --------------------------
# # Celery details
# # --------------------------
CELERY_BROKER_URL = config('CELERY_BROKER_URL',default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND')
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_ACKS_LATE = True
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60 

CELERY_TASK_DEFAULT_QUEUE = 'celery'
CELERY_TASK_DEFAULT_EXCHANGE = 'celery'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'celery'

CELERY_TASK_QUEUES = {
    'celery': {
        'exchange': 'celery',
        'routing_key': 'celery',
    },
    'high_priority': {
        'exchange': 'high_priority',
        'routing_key': 'high_priority',
    }
}

CELERY_TASK_ROUTES = {
    'notification_app.tasks.process_alert': {'queue': 'high_priority'},
    'sensor_app.tasks.process_sensor_batch': {'queue': 'celery'},
    'notification_app.tasks.send_alert_notification': {'queue': 'high_priority'},
}

CELERY_BEAT_SCHEDULE = {
    'check-device-connectivity-every-30-seconds': {
        'task': 'sensor_app.tasks.check_device_connectivity',
        'schedule': 30.0,
    },
    'retry-high-severity-notifications-every-5-minutes': {
        'task': 'notification_app.tasks.retry_high_severity_notifications',
        'schedule': 150.0, # 5 minutes
    },
}



STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static"
]
