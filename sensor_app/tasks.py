import json
import redis
import logging
from celery import shared_task
from datetime import datetime, timezone
from sensor_app.helperFunction import get_device, get_fluid_bag
from sensor_app.models import Device, FluidBag, SensorReading
from django.conf import settings
from django.db import transaction, DatabaseError

celery_logger = logging.getLogger('celery')

r = redis.Redis.from_url(settings.REDIS_URL)

QUEUE_KEY = "sensor_queue"
LOCK_KEY = "sensor_batch_lock"
DEBOUNCE_KEY = "sensor_batch_debounce"
BATCH_SIZE = 500


@shared_task(queue='high_priority')
def process_alert(payload):
    try:
        celery_logger.info(f"🔔 Processing alert for payload: {payload}")
        
        node_id = payload.get('node_id')
        reading = payload.get('reading')
        
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


def acquire_lock(lock_key, timeout=15):
    return r.set(lock_key, "1", nx=True, ex=timeout)


def release_lock(lock_key):
    r.delete(lock_key)


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue='celery')
def process_sensor_batch(self):
    celery_logger.info("📦 Starting batch processing...")
  
    if not acquire_lock(LOCK_KEY, timeout=20):
        celery_logger.info("🔒 Lock already acquired, skipping batch")
        return

    try:
        batch = []
        for _ in range(BATCH_SIZE):
            data = r.rpop(QUEUE_KEY)
            if not data:
                break
            batch.append(json.loads(data))

        if not batch:
            celery_logger.info("📭 No data in queue")
            return

        celery_logger.info(f"📊 Processing batch of {len(batch)} messages")

        # Fetch all devices & fluidbags in one go
        node_ids = {str(item["node_id"]) for item in batch}
        devices = Device.objects.filter(id__in=node_ids).in_bulk(field_name="id")
        fluid_bags = FluidBag.objects.filter(device_id__in=node_ids).in_bulk(field_name="device_id")

        celery_logger.info(f"Found {len(devices)} devices and {len(fluid_bags)} fluid bags")

        readings_to_insert = []
        for msg in batch:
            node_id = str(msg["node_id"])
            device = devices.get(node_id)
            if not device:
                celery_logger.warning(f"⚠️ Device {node_id} not found in batch")
                continue

            fluid_bag = fluid_bags.get(device.id)
            if not fluid_bag:
                celery_logger.warning(f"⚠️ FluidBag not found for device {node_id}")
                continue

            ts = datetime.fromtimestamp(msg["timestamp"], tz=timezone.utc)
            
            reading_value = msg.get("reading")
            if reading_value is None:
                celery_logger.warning(f"⚠️ No 'reading' field in message: {msg}")
                continue

            readings_to_insert.append(
                SensorReading(
                    fluidBag=fluid_bag,
                    reading=int(reading_value),
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
            celery_logger.info(f"✅ Bulk inserted {len(readings_to_insert)} readings")
        else:
            celery_logger.warning("⚠️ No valid readings to insert")

    except DatabaseError as db_err:
        celery_logger.error(f"❌ DB Error during batch insert: {db_err}")
        self.retry(exc=db_err)

    except Exception as e:
        celery_logger.error(f"❌ Unexpected error in batch insert: {e}", exc_info=True)

    finally:
        release_lock(LOCK_KEY)


def trigger_batch_task():
    if not r.exists(DEBOUNCE_KEY):
        r.set(DEBOUNCE_KEY, "1", ex=3)
        celery_logger.info("🚀 Triggering batch task")
        process_sensor_batch.delay()
    else:
        celery_logger.debug("⏸️ Batch task debounced")


@shared_task(queue='high_priority')
def send_alert_notification(node_id=None):
    celery_logger.info(f"📧 Alert notification for node {node_id}")
    # TODO: Implement alert notification logic
    pass