from .base import *
import os

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Ajouter ces configurations pour allauth
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = 5
ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT = 300

# En développement, les emails sont affichés dans la console au lieu d'être réellement envoyés
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Google OAuth2
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('770813686548-7ud3quh5kflk7ntm4gv9au7g2vual01k.apps.googleusercontent.com'),
            'secret': os.environ.get('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'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'VERIFIED_EMAIL': True,
    }
}

# Frontend URL
FRONTEND_URL = 'http://localhost:5173'

# Sites framework
SITE_ID = 1