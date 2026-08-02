"""
Django settings for config project.
"""

from pathlib import Path
from decouple import config
from datetime import timedelta

# BASE_DIR remonte de 3 niveaux car base.py est dans config/settings/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',

    #Local Apps
    'apps.accounts',
    'apps.investors',
    'apps.companies',
    'apps.projects',
    'apps.wallets', 
    'apps.transactions',
]

# Configuration de Django REST Framework
REST_FRAMEWORK = {
    # Toutes les vues sont authentifiées par JWT par défaut
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    # Par défaut, une requête doit être authentifiée (sécurité par défaut, on ouvrira au cas par cas)
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# Configuration des tokens JWT (durées, rotation, sécurité)
SIMPLE_JWT = {
    # Durée de vie de l'access token, lue depuis .env (JWT_ACCESS_MINUTES=10)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_MINUTES', default=10, cast=int)),

    # Durée de vie du refresh token, lue depuis .env (JWT_REFRESH_DAYS=5)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_DAYS', default=5, cast=int)),

    # Génère un nouveau refresh token à chaque rafraîchissement (sécurité renforcée)
    'ROTATE_REFRESH_TOKENS': True,

    # Ajoute l'ancien refresh token à la blacklist après rotation
    'BLACKLIST_AFTER_ROTATION': True,

    # Met à jour last_login de l'utilisateur à chaque connexion
    'UPDATE_LAST_LOGIN': True,

    # Algorithme de signature du token
    'ALGORITHM': 'HS256',

    # Clé secrète utilisée pour signer les tokens (différente de SECRET_KEY Django)
    'SIGNING_KEY': config('JWT_SECRET_KEY'),

    # Type d'en-tête HTTP attendu : "Authorization: Bearer <token>"
    'AUTH_HEADER_TYPES': ('Bearer',),

    # Champ utilisé comme identifiant dans le payload du token
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

AUTH_USER_MODEL = 'accounts.CustomUser'
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Type de clé primaire par défaut pour tous les modèles
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuration des fichiers uploadés par les utilisateurs (photos, documents KYC)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'