# sensor_app/tasks.py
import logging
from celery import shared_task
from django.core.mail import send_mail
from sensor_app.models import SensorReading

celery_logger = logging.getLogger('celery')

@shared_task
def send_alert_notification(sensor_reading_id):
    """Send email/SMS alert for critical sensor readings"""
    reading = SensorReading.objects.get(id=sensor_reading_id)
    
    if reading.status in ['LOW', 'CRITICAL']:
        celery_logger.info('Email send but actually email lgoin depend')
        # Send email
        # send_mail(
        #     f'Alert: {reading.fluidBag.type} Level {reading.status}',
        #     f'Device {reading.fluidBag.device.mac_address} reported {reading.status} level: {reading.fluid_level}ml',
        #     'system@hospital.com',
        #     ['nurse@hospital.com'],
        # )