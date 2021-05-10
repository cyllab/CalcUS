import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    is_test = os.environ['CALCUS_TEST']
except:
    is_test = False
else:
    is_test = True

if is_test:
    SECRET_KEY = "testkey"
else:
    SECRET_KEY = os.environ['CALCUS_SECRET_KEY']


DEBUG = False
PROD = False

ALLOWED_HOSTS = '*.*.*.*'

if not DEBUG and PROD:
    ALLOWED_HOSTS = '*.*.*.*'
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    #SECURE_REFERRER_POLICY = origin
    X_FRAME_OPTIONS = 'DENY'

INSTALLED_APPS = [
    'frontend',
    'bulma',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
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


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'OPTIONS': {
            'timeout': 100,
            },
        'TEST': {
            'NAME': '/tmp/testdb.sqlite3',
            }
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

LOGIN_REDIRECT_URL = '/home'

DEFAULT_FROM_EMAIL = 'bot@CalcUS'
if is_test:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = os.path.join(BASE_DIR, "frontend", "tests", "sent_emails")

MEDIA_URL = '/media/'

AXES_LOCKOUT_TEMPLATE = 'registration/lockout.html'

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

ALLOW_LOCAL_CALC = True

PING_HOME = False
with open("/etc/machine-id") as f:
    MACHINE_ID = f.readlines()[0].strip()
