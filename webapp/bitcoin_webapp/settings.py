"""
Django settings for bitcoin_webapp project.

Generated for Bitcoin Trading Data Visualization Web Application.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-local-dev-bitcoin-trading-app-change-in-production'
)

# Warn if using default secret key
if SECRET_KEY == 'django-insecure-local-dev-bitcoin-trading-app-change-in-production':
    import warnings
    warnings.warn(
        "WARNING: Using default SECRET_KEY. Set DJANGO_SECRET_KEY environment variable for production!",
        RuntimeWarning
    )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

# Parse ALLOWED_HOSTS from environment variable (comma-separated)
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'rest_framework',
    'corsheaders',
    # Local apps
    'charts',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bitcoin_webapp.urls'

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

WSGI_APPLICATION = 'bitcoin_webapp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # CRITICAL: Point to existing database in parent directory
        'NAME': Path(os.getenv('BTC_DB_PATH', str(BASE_DIR.parent / 'btc_eur_data.db'))),
        'OPTIONS': {
            'timeout': 20,  # Increase timeout for busy database
            'check_same_thread': False,  # Allow multi-threaded access (required for SQLite in production)
        },
        # Connection pooling: Keep connections alive for reuse
        # In development (DEBUG=True), close connections after each request (CONN_MAX_AGE=0)
        # In production (DEBUG=False), keep connections for 60 seconds to reduce overhead
        'CONN_MAX_AGE': 0 if DEBUG else 60,
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'Europe/Berlin'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 1000,
    'DEFAULT_PERMISSION_CLASSES': [
        # No authentication required for local development
        'rest_framework.permissions.AllowAny',
    ]
}


# CORS settings
# Parse CORS_ALLOWED_ORIGINS from environment variable (comma-separated)
cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]

# Only allow all origins if explicitly set (for development)
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL', 'False') == 'True'

# Warn if CORS_ALLOW_ALL_ORIGINS is True
if CORS_ALLOW_ALL_ORIGINS:
    import warnings
    warnings.warn(
        "WARNING: CORS_ALLOW_ALL_ORIGINS is True. This should only be used in development!",
        RuntimeWarning
    )


# Binance API Configuration
# SECURITY: API keys should be read-only with no trading permissions
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Warn if API keys are not configured
if not BINANCE_API_KEY or not BINANCE_API_SECRET:
    import warnings
    warnings.warn(
        "WARNING: Binance API keys not configured. Trading performance features will be disabled. "
        "Set BINANCE_API_KEY and BINANCE_API_SECRET environment variables.",
        RuntimeWarning
    )
