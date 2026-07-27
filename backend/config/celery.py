import os

import django
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('industrial_prospecting')

# Asegura que Django esté inicializado antes de descubrir tareas
# (config_from_object por sí solo no es suficiente en Celery 5.4 + Django 6.0)
django.setup()

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    self.request
