import json
import uuid
import redis
import logging
from celery import shared_task
from datetime import datetime, timezone as dt_timezone
from sensor_app.helperFunction import get_device, get_fluid_bag
from sensor_app.models import Device, FluidBag, SensorReading
from django.conf import settings

celery_logger = logging.getLogger('celery')

r = redis.Redis.from_url(settings.REDIS_URL)

@shared_task(queue='high_priority')
def process_alert(payload):
    try:
        celery_logger.info(f"📢 Processing alert for payload: {payload}")
        
        node_id = payload.get('node_id')
        reading = payload.get('reading')
        battery = payload.get('battery_percent')
        
        if not reading:
            celery_logger.warning(f"No reading value in payload")
            return 'NO_READING'
        
        device = get_device(node_id)
        fluid_bag = get_fluid_bag(device)
        
        if not fluid_bag:
            celery_logger.warning(f"No fluid bag found for device {node_id}")
            return 'NO_FLUID_BAG'

        bag_type = fluid_bag.type.lower()
    
        if bag_type == 'iv_bag':
            if reading <= fluid_bag.threshold_low:
                celery_logger.warning(f'⚠️ ALERT: IV bag level LOW for device {node_id}')
                return 'ALERT: IV bag level LOW'
            else:
                return 'NORMAL'
        
        elif bag_type in ('blood_bag', 'urine_bag'):
            if reading >= fluid_bag.threshold_high:
                celery_logger.warning(f'⚠️ ALERT: {bag_type} level HIGH for device {node_id}')
                return f'ALERT: {bag_type.replace("_", " ").title()} level HIGH'
            else:
                return 'NORMAL'
        
        else:
            return 'NORMAL'
        
    except Device.DoesNotExist:
        celery_logger.error(f'❌ Device not found: {node_id}')
        return 'DEVICE_NOT_FOUND'
    except Exception as e:
        celery_logger.error(f'❌ Alert processing failed: {e}', exc_info=True)
        return 'ERROR'


@shared_task(queue='high_priority')
def send_alert_notification(node_id=None):
    celery_logger.info(f"📧 Alert notification for node {node_id}")
    # TODO: Implement alert notification logic
    pass