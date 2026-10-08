import os
import random
import string
from pathlib import Path
from . import custom_settings

ENTERPRISE_EDITION = False
# Development Mode
DEBUG = custom_settings.DEV_MODE
DESKTOP_MODE = custom_settings.DESKTOP_MODE
BASE_DIR = custom_settings.BASE_DIR
HOME_DIR = custom_settings.HOME_DIR
MAX_UPLOAD_SIZE = custom_settings.MAX_UPLOAD_SIZE
APP_DB_NAME = custom_settings.APP_DB_NAME
SUPPORTED_POSTGRES_VERSIONS = [13, 14, 15, 16, 17, 18]

TEMP_DIR = os.path.join(BASE_DIR,'app','static','temp')
PLUGINS_DIR = os.path.join(BASE_DIR,'app','plugins')
PLUGINS_STATIC_DIR = os.path.join(BASE_DIR,'app','static','plugins')
APP_DIR = os.path.join(BASE_DIR,'app')

SESSION_COOKIE_SECURE = custom_settings.SESSION_COOKIE_SECURE
CSRF_COOKIE_SECURE = custom_settings.CSRF_COOKIE_SECURE
CSRF_TRUSTED_ORIGINS = []
SESSION_COOKIE_NAME = 'pgmanage_sessionid'
CSRF_COOKIE_NAME = 'pgmanage_csrftoken'
ALLOWED_HOSTS = ['*']
SQLITE_PATH = os.path.join(HOME_DIR, f'{APP_DB_NAME}.db')
if not DESKTOP_MODE:
    SQLITE_PATH = os.path.join(HOME_DIR, f'{APP_DB_NAME}-server.db')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': SQLITE_PATH
    }
}

if DEBUG:
    SECRET_KEY = 'ijbq-+%n_(_^ct+qnqp%ir8fzu3n#q^i71j4&y#-6#qe(dx!h3'
else:
    SECRET_KEY = ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(50))

INSTALLED_APPS = [
    'app',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_vite',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.DataUnpackMiddleware'
]

ROOT_URLCONF = 'pgmanage.urls'

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

WSGI_APPLICATION = 'pgmanage.wsgi.application'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]


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

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

PATH = custom_settings.PATH
# Processing PATH
if PATH == '/':
    PATH = ''
elif PATH != '':
    if PATH[0] != '/':
        PATH = '/' + PATH
    if PATH[len(PATH)-1] == '/':
        PATH = PATH[:-1]


LOGIN_URL = PATH + '/pgmanage_login/'
LOGIN_REDIRECT_URL = PATH + '/'

STATIC_URL = PATH + '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "app/static")

SESSION_SERIALIZER = 'app.serializers.PickleSerializer'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

#PgManage LOGGING

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%m/%d/%Y %H:%M:%S"
        },
        'frontend_error' : {
            'format' : "[{asctime}] {levelname} [pid:{process}] [{name}:{lineno}] [request_id:{request_id}] {message}",
            'datefmt' : "%m/%d/%Y %H:%M:%S",
            'style': '{',
        },
    },
    'filters': {
        'masked_data_filter': {
            '()': 'pgmanage.logging_filter.MaskedDataFilter',
        },
    },
    'handlers': {
        "logfile_frontend": {
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(HOME_DIR, 'audaxdm.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter': 'frontend_error',
            'filters': ['masked_data_filter'],
        },
        'logfile_pgmanage': {
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(HOME_DIR, 'audaxdm.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
        },
        'logfile_django': {
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(HOME_DIR, 'audaxdm.log'),
            'maxBytes': 1024*1024*5, # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
            'level':'ERROR',
        },
        'console_django':{
            'class':'logging.StreamHandler',
            'formatter': 'standard'
        },
        'console_app':{
            'class':'logging.StreamHandler',
            'formatter': 'standard',
            'level':'ERROR',
        },
    },
    'loggers': {
        'app.views.logging' : {
            "handlers": ["logfile_frontend"],
            "propagate": False
        },
        'django': {
            'handlers':['logfile_django','console_django'],
            'propagate': False,
        },
        'app': {
            'handlers': ['logfile_pgmanage','console_app'],
            'propagate': False,
            'level':'INFO',
        },
        'cherrypy.error': {
            'handlers': ['logfile_django','console_app'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

#PgManage PARAMETERS
PGMANAGE_VERSION = custom_settings.PGMANAGE_VERSION
PGMANAGE_SHORT_VERSION = custom_settings.PGMANAGE_SHORT_VERSION
CH_CMDS_PER_PAGE = 20
PWD_TIMEOUT_TOTAL = 1800
PWD_TIMEOUT_REFRESH = 300
CLIENT_TIMEOUT = 600
THREAD_POOL_MAX_WORKERS = 2
MASTER_PASSWORD_REQUIRED = custom_settings.DESKTOP_MODE

DJANGO_VITE_DEV_MODE = DEBUG
DJANGO_VITE_DEV_SERVER_PORT = 3000

if not DEBUG:
    DJANGO_VITE_MANIFEST_PATH = os.path.join(STATIC_ROOT, "dist", '.vite', 'manifest.json')
    DJANGO_VITE_STATIC_URL_PREFIX = "dist"
    DJANGO_VITE_ASSETS_PATH = os.path.join(STATIC_ROOT, "dist")
else:
    DJANGO_VITE_ASSETS_PATH = os.path.join(STATIC_ROOT, "pgmanage_frontend")

STATICFILES_DIRS = [
    DJANGO_VITE_ASSETS_PATH,
]

if ENTERPRISE_EDITION:
    from enterprise.settings_enterprise import update_settings
    update_settings()