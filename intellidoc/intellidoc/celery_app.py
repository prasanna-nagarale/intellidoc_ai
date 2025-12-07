import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'intellidoc.settings')

app = Celery('intellidoc')

# Load custom settings from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Autodiscover tasks.py in all apps
app.autodiscover_tasks()
