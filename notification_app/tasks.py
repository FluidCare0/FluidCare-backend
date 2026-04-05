import json
import uuid
import redis
import logging
from celery import shared_task
from datetime import datetime, timedelta, timezone as dt_timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from sensor_app.helperFunction import get_device, get_fluid_bag
from sensor_app.models import Device, FluidBag, SensorReading, PatientDeviceBedAssignment
from django.conf import settings
from django.utils import timezone

from notification_app.models import Notification
from notification_app.serializers import NotificationSerializer

celery_logger = logging.getLogger('celery')

r = redis.Redis.from_url(settings.REDIS_URL)


def send_notification_to_websocket(notification):
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            serializer = NotificationSerializer(notification)
            async_to_sync(channel_layer.group_send)(
                "sensor_monitoring",
                {
                    "type": "handle_notification",
                    "notification": serializer.data
                }
            )
            celery_logger.info(f"🔔 Sent WebSocket notification: {notification.title}")
    except Exception as e:
        celery_logger.error(f"❌ WebSocket notification error: {e}")


def create_notification(device, title, message, n_type='info', severity='low'):
    patient_name = None
    assignment = PatientDeviceBedAssignment.objects.filter(device=device, end_time__isnull=True).first()
    if assignment and assignment.patient:
        patient_name = assignment.patient.name

    notification = Notification.objects.create(
        recipient=None,
        created_by=None,
        device=device,
        source='system',
        delivery_scope='global',
        target_role=None,
        patient_name=patient_name,
        title=title,
        message=message,
        notification_type=n_type,
        severity=severity,
    )
    send_notification_to_websocket(notification)
    return notification

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


@shared_task(queue="celery")
def retry_high_severity_notifications():
    unread_high_alerts = Notification.objects.filter(
        severity='high',
        is_read=False,
        is_resolved=False,
        retry_count__lt=2,
    )

    for alert in unread_high_alerts:
        last_time = alert.last_retry or alert.created_at
        if timezone.now() > last_time + timedelta(minutes=5):
            alert.retry_count += 1
            alert.last_retry = timezone.now()
            alert.save(update_fields=['retry_count', 'last_retry'])
            send_notification_to_websocket(alert)
            celery_logger.info(f"🔄 Retrying high-severity alert ({alert.retry_count + 1}/3): {alert.title}")
