import os
from celery import Celery
from celery.signals import setup_logging
import logging
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'process-sensor-batch-every-3-seconds': {
        'task': 'sensor_app.tasks.process_sensor_batch',
        'schedule': 3.0,  # every 3 seconds
    },
}