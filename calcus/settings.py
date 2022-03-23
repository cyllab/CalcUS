'''
This file of part of CalcUS.

Copyright (C) 2020-2022 Raphaël Robidas

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''


import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    IS_TEST = os.environ['CALCUS_TEST']
except:
    IS_TEST = False
else:
    IS_TEST = True

if IS_TEST:
    SECRET_KEY = "testkey"
else:
    SECRET_KEY = os.environ['CALCUS_SECRET_KEY']

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

try:
    DEBUG = os.environ['CALCUS_DEBUG']
except:
    DEBUG = False
else:
    DEBUG = True

if 'CALCUS_VERSION_HASH' in os.environ.keys():
    CALCUS_VERSION_HASH = os.environ['CALCUS_VERSION_HASH']
else:
    import subprocess

    try:
        CALCUS_VERSION_HASH = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        CALCUS_VERSION_HASH = "unknown"

PACKAGES = []
if "CALCUS_XTB" in os.environ:
    PACKAGES.append("xtb")
if "CALCUS_ORCA" in os.environ:
    PACKAGES.append("ORCA")
if "CALCUS_GAUSSIAN" in os.environ:
    PACKAGES.append("Gaussian")

SSL = False

ALLOWED_HOSTS = '*.*.*.*'

if not DEBUG and SSL:
    ALLOWED_HOSTS = '*.*.*.*'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
    'frontend',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
    'dbbackup',
    'bulma',
    #'debug_toolbar',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'calcus.urls'

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

WSGI_APPLICATION = 'calcus.wsgi.application'
DEFAULT_AUTO_FIELD='django.db.models.AutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'calcus',
        'USER': 'calcus',
        'PASSWORD': POSTGRES_PASSWORD,
        'HOST': 'postgres',
        'PORT': '5432',
    }
}

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

TIME_ZONE = 'EST'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': 'backups/'}
LOGIN_REDIRECT_URL = '/home'

DEFAULT_FROM_EMAIL = 'bot@CalcUS'

if IS_TEST:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = os.path.join(BASE_DIR, "frontend", "tests", "sent_emails")

MEDIA_URL = '/media/'

AXES_LOCKOUT_TEMPLATE = 'registration/lockout.html'
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1

THROTTLE_ZONES = {
    'load_remote_log': {
        'VARY':'throttle.zones.RemoteIP',
        'NUM_BUCKETS':2,
        'BUCKET_INTERVAL':600,#seconds, I assume
        'BUCKET_CAPACITY':10,
    },
}

THROTTLE_BACKEND = 'throttle.backends.cache.CacheBackend'

THROTTLE_ENABLED = True

MAX_UPLOAD_SIZE = "2621440"#2.5MB max
INTERNAL_IPS = [
    '127.0.0.1',
]

SESSION_COOKIE_NAME = "CALCUS_SESSION_COOKIE"

ALLOW_LOCAL_CALC = True

DBBACKUP_CLEANUP_KEEP = 10 # Number of old DBs to keep
DBBACKUP_INTERVAL = 1 # In days (can be a float)

PING_SATELLITE = os.getenv("CALCUS_PING_SATELLITE", "False")
PING_CODE = os.getenv("CALCUS_PING_CODE", "default")
