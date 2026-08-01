from .base import *

DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# En développement, les emails sont affichés dans la console au lieu d'être réellement envoyés
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# URL du frontend, utilisée pour construire le lien d'activation envoyé par email
FRONTEND_URL = 'http://localhost:5173'