"""
Django settings for heystox_trade project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from kombu import Queue
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'o!%%y@$!_ms9)z1%!yy_qn0d-=3gx=(1-*!(wrs-pi*n0no3pf'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "market_analysis.apps.MarketAnalysisConfig",
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_celery_beat',
    'django_celery_results',
    'rest_framework',
    'django_filters',
    'rest_framework.authtoken',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'market_analysis.middleware.UserAuthRequired',
]

ROOT_URLCONF = 'heystox_trade.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'heystox_trade.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

# Remote Data Base
# Use ssh -i heystox_makki -L 9211:localhost:5432 heystox@139.59.90.114 for tunneling with remote data
# heystox_makki = ssh key, 9211 is local machine port, 5432 is server machine psql port, then user then ip address

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'heystox',                      # Or path to database file if using sqlite3.
        'USER': 'heystox',                      # Not used with sqlite3.
        'PASSWORD': 's1rshopalot',                  # Not used with sqlite3.
        'HOST': 'localhost',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '9211',                 # Set to empty string for default. Not used with sqlite3.
    }
}

# Local Data Base

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'testdb',
#         'USER': 'testdb',
#         'PASSWORD': '123456',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }



# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(os.getcwd()),'static/')
# Cache

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.dirname(os.getcwd()) + "/cache",
        'TIMEOUT': None,
        'OPTIONS': {
            'MAX_ENTRIES': 2000
        }
    },
    "redis": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379",
        'TIMEOUT': None,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient"
        },
    }
}

APPEND_SLASH = True


# NSE HEADERS 
NSE_HEADERS = {"Host": "www1.nseindia.com", "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": "1", 
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            }



# UPSTOX API
UPSTOX_REDIRECT_URL = "http://127.0.0.1:8000/"

# CELERY STUFF
# CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_BROKER_URL = 'pyamqp://guest@localhost//'
# CELERY_RESULT_BACKEND = 'pyamqp://guest@localhost//'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_RESULT_BACKEND = 'redis'
CELERY_RESULT_EXPIRES = 21600*3
CELERY_IMPORTS = ('market_analysis.tasks')
CELERY_DEFAULT_QUEUE = "low_priority"


CELERY_WORKER_POOL_RESTARTS = True

CELERY_QUEUES = (
    Queue("low_priority"),
    Queue("medium_priority"),
    Queue("high_priority"),
)
CELERY_CACHE_BACKEND = "redis"




# SLACK SETTINGS

SLACK_TOKEN = 'xoxp-792096669381-779313280690-793468872963-37b278cd3fab65d3d0b16de3c8747123'
SLACK_WEBHOOK = "https://hooks.slack.com/services/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"

# LOGIN URL
LOGIN_URL = "/login/"
# LOGIN_REDIRECT_URL = "/dashboard/sorted-stocks/"

# LOGIN Redirect Exempted Url
LOGIN_REDIRECT_EXEMPTED_URLS = [LOGIN_URL, "/admin/login/"]

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # 'DEFAULT_PERMISSION_CLASSES': [
    #     'rest_framework.permissions.IsAuthenticated',
    # ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ]
}

# Imports Additional Settings File
try:
    from .local_settings import *
except ImportError:
    pass