import os
from celery import Celery

# Indique a Celery ou trouver les settings Django, AVANT toute autre chose
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("crowdfunding_platform")

# Charge la config Celery depuis les settings Django (variables prefixees CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Decouvre automatiquement les fichiers tasks.py dans toutes les apps INSTALLED_APPS
app.autodiscover_tasks()
