"""
Django settings for config project.
"""

from pathlib import Path
from decouple import config
from datetime import timedelta
from decimal import Decimal

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
    'rest_framework.authtoken', 
    'django.contrib.staticfiles',
    'corsheaders',

    # Third-party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'whitenoise.runserver_nostatic',

    #Local Apps
    'django_celery_results',
    'apps.accounts',
    'apps.investors',
    'apps.companies',
    'apps.projects',
    'apps.wallets', 
    'apps.transactions',
    'apps.investments',
    'apps.repayments',
    'apps.notifications', 
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
     # Indique a DRF d'utiliser drf-spectacular pour generer le schema OpenAPI
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
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
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'VOTRE_CLIENT_ID_GOOGLE',
            'secret': 'VOTRE_SECRET_GOOGLE',
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'VERIFIED_EMAIL': True,
    }
}

# Redirection après connexion Google
LOGIN_REDIRECT_URL = 'http://localhost:5173/auth/google/callback'
SOCIALACCOUNT_LOGIN_ON_GET = True

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

# ============================================
# Configuration drf-spectacular (documentation API)
# ============================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'Crowdfunding Platform API',
    'DESCRIPTION': (
        "API REST complete pour une plateforme de crowdfunding : "
        "authentification JWT, profils KYC/KYB, projets, investissements, "
        "wallets, transactions et remboursements."
    ),
    'VERSION': '1.0.0',

    'SERVE_INCLUDE_SCHEMA': False,

    'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+/',

    'TAGS': [
        {'name': 'accounts', 'description': 'Authentification, activation, reset de mot de passe'},
        {'name': 'investors', 'description': 'Profils investisseurs et KYC'},
        {'name': 'companies', 'description': 'Profils entreprises et KYB'},
        {'name': 'projects', 'description': 'Campagnes de crowdfunding'},
        {'name': 'wallets', 'description': 'Portefeuilles financiers'},
        {'name': 'transactions', 'description': 'Depots, retraits, investissements'},
        {'name': 'investments', 'description': 'Portefeuille d\'investissements'},
        {'name': 'repayments', 'description': 'Plans et echeances de remboursement'},
        {'name': 'notifications', 'description': 'Notifications in-app'},
    ],

    'ENUM_NAME_OVERRIDES': {
        'InvestmentStatusEnum': [
            ('ACTIVE', 'Actif'),
            ('REFUNDED', 'Rembourse'),
            ('PARTIALLY_REFUNDED', 'Partiellement rembourse'),
        ],

        'ProjectStatusEnum': [
            ('DRAFT', 'Brouillon'),
            ('PENDING', 'En attente de validation'),
            ('NEEDS_CORRECTION', 'Corrections demandées'),
            ('APPROVED', 'Approuvé'),
            ('REJECTED', 'Refusé'),
            ('ACTIVE', 'Actif (collecte en cours)'),
            ('COMPLETED', 'Terminé'),
            ('CANCELLED', 'Annulé'),
        ],

        'RepaymentPlanStatusEnum': [
            ('DRAFT', 'Brouillon'),
            ('ACTIVE', 'Actif'),
            ('COMPLETED', 'Terminé'),
            ('DEFAULTED', 'En défaut'),
        ],

        'RepaymentStatusEnum': [
            ('SCHEDULED', 'Planifiée'),
            ('PAID', 'Payée'),
            ('LATE', 'En retard'),
            ('CANCELLED', 'Annulée'),
        ],

        'TransactionStatusEnum': [
            ('PENDING', 'En attente'),
            ('COMPLETED', 'Terminée'),
            ('FAILED', 'Échouée'),
            ('CANCELLED', 'Annulée'),
        ],
    },
}

# ============================================
# Configuration Celery
# ============================================
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# En mode test, exécute les tâches Celery de façon SYNCHRONE et immédiate,
# sans passer par Redis -- élimine toute dépendance externe pendant les tests.
import sys
if 'test' in sys.argv:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Taux de commission prélevé par la plateforme sur les INTÉRÊTS versés
# aux investisseurs (jamais sur le capital, qui reste intégralement remboursé).
PLATFORM_COMMISSION_RATE = config('PLATFORM_COMMISSION_RATE', default='10.00', cast=Decimal)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} - {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'apps.transactions': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"