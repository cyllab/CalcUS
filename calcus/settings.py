"""
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
"""


import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IS_CLOUD = "CALCUS_CLOUD" in os.environ
IS_TEST = "CALCUS_TEST" in os.environ


try:
    DEBUG = os.environ["CALCUS_DEBUG"]
except:
    DEBUG = False
else:
    DEBUG = True

if IS_TEST or DEBUG:
    SECRET_KEY = "testkey"
    SILENCED_SYSTEM_CHECKS = ["captcha.recaptcha_test_key_error"]
else:
    SECRET_KEY = os.environ["CALCUS_SECRET_KEY"]

if "CALCUS_VERSION_HASH" in os.environ.keys():
    CALCUS_VERSION_HASH = os.environ["CALCUS_VERSION_HASH"]
else:
    import subprocess

    try:
        CALCUS_VERSION_HASH = (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("utf-8")
            .strip()
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        CALCUS_VERSION_HASH = "unknown"


POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "calcus")

GMAIL_API_CLIENT_ID = os.getenv("CALCUS_EMAIL_ID", "")
GMAIL_API_CLIENT_SECRET = os.getenv("CALCUS_EMAIL_SECRET", "")
GMAIL_API_REFRESH_TOKEN = os.getenv("CALCUS_EMAIL_TOKEN", "")

ALLOWED_HOSTS = [
    "0.0.0.0",
    "0.0.0.0:*",
    "https://calcus.cloud",
    "calcus.cloud",
    "localhost",
    "cloud-compute",
    "cloud-compute:*",
]

CSRF_TRUSTED_ORIGINS = ["calcus.cloud"]

if "CALCUS_CLOUD_INTERNAL" in os.environ:
    ALLOWED_HOSTS.append("*")
    CSRF_TRUSTED_ORIGINS.append("*")

if IS_TEST:
    ALLOWED_HOSTS.append("*")
    ALLOWED_HOSTS.append("*.*.*.*")
    ALLOWED_HOSTS.append("*.*.*.*:*")

    CSRF_TRUSTED_ORIGINS.append("*")
    CSRF_TRUSTED_ORIGINS.append("*.*.*.*")
    CSRF_TRUSTED_ORIGINS.append("*.*.*.*:*")

INSTALLED_APPS = [
    "frontend",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "bulma",
    "gmailapi_backend",
    #'debug_toolbar',
]

if IS_CLOUD:
    INSTALLED_APPS.append("captcha")

    if not DEBUG:
        SECURE_SSL_REDIRECT = True
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
        RECAPTCHA_PUBLIC_KEY = os.getenv(
            "RECAPTCHA_PUBLIC_KEY", "6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"
        )
        RECAPTCHA_PRIVATE_KEY = os.getenv(
            "RECAPTCHA_PRIVATE_KEY", "6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe"
        )
else:
    INSTALLED_APPS.append("dbbackup")

    DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
    DBBACKUP_STORAGE_OPTIONS = {"location": "/calcus/backups/"}
    DBBACKUP_CLEANUP_KEEP = 10  # Number of old DBs to keep
    DBBACKUP_INTERVAL = 1  # In days (can be a float)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
]

HASHID_FIELD_SALT = os.getenv("CALCUS_HASHID_SALT", "test_salt")

AUTH_USER_MODEL = "frontend.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "calcus.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "frontend.context.default",
            ],
        },
    },
]

WSGI_APPLICATION = "calcus.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "calcus",
        "USER": POSTGRES_USER,
        "PASSWORD": POSTGRES_PASSWORD,
        "HOST": POSTGRES_HOST,
        "PORT": "5432",
    }
}

# In Cloud mode, we need to constantly query the database to check if the
# running calculation has been cancelled. This is the delay between checks in seconds.
DATABASE_STATUS_CHECK_DELAY = 2


if os.environ.get("IS_TEST_CLUSTER_DAEMON", "") != "":
    DATABASES["default"]["NAME"] = "test_calcus"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

DEFAULT_AUTO_FIELD = "hashid_field.BigHashidAutoField"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "EST"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = os.getenv("STATIC_URL", "/static/")

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

LOGIN_REDIRECT_URL = "/home"

DEFAULT_FROM_EMAIL = "bot@calcus.cloud"

if IS_TEST:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = os.path.join(BASE_DIR, "scratch", "sent_emails")
else:
    EMAIL_BACKEND = "gmailapi_backend.mail.GmailBackend"

MEDIA_URL = "/media/"

AXES_LOCKOUT_TEMPLATE = "registration/lockout.html"
AXES_FAILURE_LIMIT = 10
AXES_COOLOFF_TIME = 1

THROTTLE_ZONES = {
    "load_remote_log": {
        "VARY": "throttle.zones.RemoteIP",
        "NUM_BUCKETS": 2,
        "BUCKET_INTERVAL": 600,  # seconds, I assume
        "BUCKET_CAPACITY": 30,
    },
}

THROTTLE_BACKEND = "throttle.backends.cache.CacheBackend"
THROTTLE_ENABLED = True

MAX_UPLOAD_SIZE = "5242880"  # 5MB max
INTERNAL_IPS = [
    "127.0.0.1",
]

SESSION_COOKIE_NAME = "CALCUS_SESSION_COOKIE"

PACKAGES = ["xtb"]

if IS_CLOUD:
    PING_SATELLITE = False

    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCP_LOCATION = os.getenv("GCP_LOCATION")
    GCP_SERVICE_ACCOUNT_EMAIL = os.getenv("GCP_SERVICE_ACCOUNT_EMAIL")
    COMPUTE_SMALL_HOST_URL = os.getenv("COMPUTE_SMALL_HOST_URL")
    COMPUTE_MEDIUM_HOST_URL = os.getenv("COMPUTE_MEDIUM_HOST_URL")
    COMPUTE_LARGE_HOST_URL = os.getenv("COMPUTE_LARGE_HOST_URL")
    ACTION_HOST_URL = os.getenv("ACTION_HOST_URL", COMPUTE_SMALL_HOST_URL)

    ALLOW_LOCAL_CALC = True
    ALLOW_REMOTE_CALC = False

    ALLOW_TRIAL = True
    # Give 60 free CPU-seconds for trial
    TRIAL_DEFAULT_COMP_SECONDS = 60

    LOCAL_MAX_ATOMS = 200

    LOCAL_ALLOWED_THEORY_LEVELS = [
        "xtb",
        # "semiempirical",
        # "hf",
        # "special",  # hf3c, pbeh3c, r2scan3c, b973c
        # "dft",
        # "mp2",
        # "cc",
    ]

    LOCAL_ALLOWED_STEPS = [
        "Geometrical Optimisation",
        "Conformational Search",
        "Constrained Optimisation",
        "Frequency Calculation",
        "TS Optimisation",
        "UV-Vis Calculation",
        "Single-Point Energy",
        # "Minimum Energy Path",
        "Constrained Conformational Search",
        # "NMR Prediction",
        # "MO Calculation",
    ]

else:
    ALLOW_LOCAL_CALC = True
    ALLOW_REMOTE_CALC = True
    ALLOW_TRIAL = False

    # For local calculations, limit the size of systems to this number of atoms or disable the limitation with -1
    LOCAL_MAX_ATOMS = -1

    # For local calculations, only allow these theory levels to be used (using the ccinput theory levels)
    LOCAL_ALLOWED_THEORY_LEVELS = [
        "ALL",  # Allows all theory levels
    ]

    LOCAL_ALLOWED_STEPS = [
        "ALL",  # Allows all steps
    ]

    PING_SATELLITE = os.getenv("CALCUS_PING_SATELLITE", "False")
    PING_CODE = os.getenv("CALCUS_PING_CODE", "default")

    if "CALCUS_ORCA" in os.environ or IS_TEST:
        PACKAGES.append("ORCA")
    if "CALCUS_GAUSSIAN" in os.environ or IS_TEST:
        PACKAGES.append("Gaussian")
