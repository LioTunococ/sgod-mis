from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]  # .../SGOD_Project

SECRET_KEY = os.getenv('SECRET_KEY', 'dev-insecure-key-change-me')
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',') if os.getenv('ALLOWED_HOSTS') else []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Project apps
    'accounts',
    'organizations',
    'submissions',
    'dashboards',
    'common',
    'notifications',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'dashboards.middleware.CacheHeaderMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dashboards.middleware.PerformanceMonitoringMiddleware',
    'dashboards.middleware.DatabaseConnectionPoolMiddleware',
]

ROOT_URLCONF = 'sgod_mis.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'accounts.context_processors.user_role_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'sgod_mis.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': str(BASE_DIR / 'db.sqlite3'),
    }
}

# Caching configuration for performance optimization
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# Cache settings for dashboard optimization
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'sgod_dashboard'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = str(BASE_DIR / 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_REDIRECT_URL = 'accounts:post_login_redirect'
LOGOUT_REDIRECT_URL = 'login'

# Increased field upload limit to accommodate large multi-tab submission form posts
# (SLP matrix + analysis + interventions + RMA + projects). Default Django limit is 1000.
# Adjusted to 20000 to prevent TooManyFieldsSent errors while retaining reasonable protection.
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000

# --- Email / Notifications ---
# Console backend by default (safe for dev). Override via env in prod.
"""Email / Notifications configuration

Priority (by environment):
1) ANYMAIL_PROVIDER is set -> use Anymail HTTP API backend (PythonAnywhere-friendly)
2) EMAIL_BACKEND is set -> honor explicitly
3) Default to console backend for local dev
"""

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'no-reply@localhost')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# 1) Anymail (HTTP API; recommended for PythonAnywhere free)
ANYMAIL_PROVIDER = os.getenv('ANYMAIL_PROVIDER', '').strip().lower()
if ANYMAIL_PROVIDER:
    EMAIL_BACKEND = f"anymail.backends.{ANYMAIL_PROVIDER}.EmailBackend"
    # Accept both MAILGUN_SENDER_DOMAIN and MAILGUN_DOMAIN for convenience
    _mailgun_sender_domain = os.getenv('MAILGUN_SENDER_DOMAIN') or os.getenv('MAILGUN_DOMAIN', '')
    ANYMAIL = {
        # Mailgun
        'MAILGUN_API_KEY': os.getenv('MAILGUN_API_KEY', ''),
        'MAILGUN_SENDER_DOMAIN': _mailgun_sender_domain,
        # SendGrid
        'SENDGRID_API_KEY': os.getenv('SENDGRID_API_KEY', ''),
        # Mailjet
        'MAILJET_API_KEY': os.getenv('MAILJET_API_KEY', ''),
        'MAILJET_SECRET_KEY': os.getenv('MAILJET_SECRET_KEY', ''),
    }
else:
    # 2) Respect explicit EMAIL_BACKEND if provided; else default to console
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Optional SMTP settings (used when EMAIL_BACKEND is SMTP)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587')) if os.getenv('EMAIL_HOST') else 587
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1').lower() in {'1','true','yes','on'}
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', '0').lower() in {'1','true','yes','on'}
if EMAIL_USE_SSL:
    EMAIL_USE_TLS = False  # mutually exclusive

# Notifications behaviour: set to '1' to send immediately upon queue
NOTIFICATIONS_SEND_IMMEDIATELY = os.getenv('NOTIFICATIONS_SEND_IMMEDIATELY', '0').lower() in {'1','true','yes','on'}

# If DEFAULT_FROM_EMAIL not provided and Mailgun sender domain exists, derive a sensible default
if DEFAULT_FROM_EMAIL == 'no-reply@localhost':
    _derived_sender_domain = os.getenv('MAILGUN_SENDER_DOMAIN') or os.getenv('MAILGUN_DOMAIN')
    if _derived_sender_domain:
        DEFAULT_FROM_EMAIL = f"no-reply@{_derived_sender_domain}"
        SERVER_EMAIL = DEFAULT_FROM_EMAIL

