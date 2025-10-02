import json
import redis
import logging
from celery import shared_task
from datetime import datetime
from django.core.mail import send_mail
from sensor_app.helperFunction import get_device, get_fluid_bag
from sensor_app.models import SensorReading
from django.conf import settings
from django.db import transaction, DatabaseError

celery_logger = logging.getLogger('celery')

r = redis.Redis.from_url(settings.REDIS_URL)

QUEUE_KEY = "sensor_queue"
LOCK_KEY = "sensor_batch_lock"
DEBOUNCE_KEY = "sensor_batch_debounce"
BATCH_SIZE = 500


@shared_task
def process_alert(payload):
    try:
        node_id = payload.get('node_id')
        reading = payload.get('reading')
        device = get_device(node_id)
        fluid_bag = get_fluid_bag(device)

        bag_type = fluid_bag.type.lower()  # assuming 'type' field exists
    
        if bag_type == 'iv_bag':
            if reading <= fluid_bag.threshold_low:
                return 'ALERT: IV bag level LOW'
            else:
                return 'NORMAL'
        
        elif bag_type in ('blood_bag', 'urine_bag'):
            if reading >= fluid_bag.threshold_high:
                return f'ALERT: {bag_type.replace("_", " ").title()} level HIGH'
            else:
                return 'NORMAL'
        
        else:
            # fallback for unknown bag types
            return 'NORMAL'
        
    except Exception as e:
        celery_celery_logger.error('Alert fail')

def acquire_lock(lock_key, timeout=15):
    return r.set(lock_key, "1", nx=True, ex=timeout)

def release_lock(lock_key):
    r.delete(lock_key)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_sensor_batch(self):
  
    if not acquire_lock(LOCK_KEY, timeout=20):
        return

    try:
        batch = []
        for _ in range(BATCH_SIZE):
            data = r.rpop(QUEUE_KEY)
            if not data:
                break
            batch.append(json.loads(data))

        if not batch:
            return

        # Fetch all devices & fluidbags in one go
        node_ids = {str(item["node_id"]) for item in batch}
        devices = Device.objects.filter(id__in=node_ids).in_bulk(field_name="id")
        fluid_bags = FluidBag.objects.filter(device_id__in=node_ids).in_bulk(field_name="device_id")

        readings_to_insert = []
        for msg in batch:
            node_id = str(msg["node_id"])
            device = devices.get(node_id)
            if not device:
                continue

            fluid_bag = fluid_bags.get(device.id)
            if not fluid_bag:
                continue

            ts = datetime.fromtimestamp(msg["timestamp"], tz=timezone.utc)

            readings_to_insert.append(
                SensorReading(
                    fluidBag=fluid_bag,
                    reading=msg.get("reading"),
                    timestamp=ts,
                    via=bool(msg.get("via")),
                    battery_percent=msg.get("battery_percent"),
                    repeater_mac=msg.get("repeater_mac"),
                    master_mac=msg.get("master_mac"),
                )
            )

        if readings_to_insert:
            with transaction.atomic():
                SensorReading.objects.bulk_create(readings_to_insert, ignore_conflicts=True)
            celery_logger.info(f"✅ Bulk inserted {len(readings_to_insert)} readings.")

    except DatabaseError as db_err:
        celery_logger.error(f"DB Error during batch insert: {db_err}")
        self.retry(exc=db_err)

    except Exception as e:
        celery_logger.error(f"Unexpected error in batch insert: {e}")

    finally:
        release_lock(LOCK_KEY)


def trigger_batch_task():
    """
    Trigger batch task with debounce (avoid rapid multiple calls)
    """
    if not r.exists(DEBOUNCE_KEY):
        r.set(DEBOUNCE_KEY, "1", ex=3)
        process_sensor_batch.delay()

@shared_task
def send_alert_notification():
    pass