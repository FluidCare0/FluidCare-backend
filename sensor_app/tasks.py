import json
import uuid
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
BATCH_SIZE = 1000  # Threshold to trigger immediate processing
MAX_BATCH_PROCESS = 5000  # Maximum items to process per periodic run


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


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue="celery")
def process_sensor_batch(self):
    celery_logger.info("📦 Starting batch processing...")

    # Acquire lock to prevent multiple workers from processing same queue
    if not acquire_lock(LOCK_KEY, timeout=20):
        celery_logger.info("🔒 Lock already acquired, skipping this run")
        return "LOCKED"

    try:
        queue_len = r.llen(QUEUE_KEY)
        celery_logger.info(f"📊 Current queue length: {queue_len}")

        if queue_len == 0:
            celery_logger.info("📭 No data in queue")
            return "EMPTY"

        batch_size = min(queue_len, MAX_BATCH_PROCESS)
        celery_logger.info(f"🎯 Processing {batch_size} items from queue")

        batch = []
        for _ in range(batch_size):
            data = r.rpop(QUEUE_KEY)
            if not data:
                break
            try:
                batch.append(json.loads(data))
            except json.JSONDecodeError as je:
                celery_logger.error(f"❌ Invalid JSON in queue: {data}, Error: {je}")

        if not batch:
            celery_logger.info("📭 No valid data in queue after parsing")
            return "NO_VALID_DATA"

        # Convert node_ids to UUID for DB lookup
        node_ids = {uuid.UUID(item["node_id"]) for item in batch}
        devices = Device.objects.filter(id__in=node_ids).in_bulk(field_name="id")

        # Fetch fluid bags and map device → first fluid bag
        fluid_bags_qs = FluidBag.objects.filter(device_id__in=node_ids).select_related("device")
        fluid_bags = {}
        for fb in fluid_bags_qs:
            if fb.device_id not in fluid_bags:
                fluid_bags[fb.device_id] = fb

        celery_logger.info(f"✅ Found {len(devices)} devices and {len(fluid_bags)} fluid bags")

        readings_to_insert = []
        errors = 0

        for msg in batch:
            try:
                node_id = uuid.UUID(msg["node_id"])
                device = devices.get(node_id)
                if not device:
                    celery_logger.warning(f"⚠️ Device {node_id} not found in batch")
                    errors += 1
                    continue

                fluid_bag = fluid_bags.get(device.id)
                if not fluid_bag:
                    celery_logger.warning(f"⚠️ FluidBag not found for device {node_id}")
                    errors += 1
                    continue

                ts = datetime.fromtimestamp(msg["timestamp"], tz=timezone.utc)
                reading_value = msg.get("reading")
                if reading_value is None:
                    celery_logger.warning(f"⚠️ No 'reading' field in message: {msg}")
                    errors += 1
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

            except Exception as msg_error:
                celery_logger.error(f"❌ Error processing message {msg}: {msg_error}")
                errors += 1

        # Bulk insert
        if readings_to_insert:
            try:
                with transaction.atomic():
                    SensorReading.objects.bulk_create(readings_to_insert, ignore_conflicts=True)
                celery_logger.info(f"✅ Successfully inserted {len(readings_to_insert)} readings")
                if errors > 0:
                    celery_logger.warning(f"⚠️ {errors} messages had errors")
                return f"SUCCESS: {len(readings_to_insert)} inserted, {errors} errors"
            except DatabaseError as db_err:
                celery_logger.error(f"❌ DB Error during bulk insert: {db_err}")
                # Push batch back to Redis for retry
                for msg in batch:
                    r.lpush(QUEUE_KEY, json.dumps(msg))
                raise  # triggers Celery retry
        else:
            celery_logger.warning(f"⚠️ No valid readings to insert ({errors} errors)")
            return f"NO_VALID_READINGS: {errors} errors"

    except DatabaseError as db_err:
        celery_logger.error(f"❌ DB Error during batch processing: {db_err}")
        self.retry(exc=db_err)

    except Exception as e:
        celery_logger.error(f"❌ Unexpected error in batch processing: {e}", exc_info=True)
        return f"ERROR: {str(e)}"

    finally:
        release_lock(LOCK_KEY)
        

def trigger_batch_task():
    """Trigger batch processing manually (when queue is full)"""
    if not r.exists(DEBOUNCE_KEY):
        r.set(DEBOUNCE_KEY, "1", ex=2)  # Reduced debounce time
        celery_logger.info("🚀 Manually triggering batch task")
        process_sensor_batch.delay()
    else:
        celery_logger.debug("⏸️ Batch task debounced")


@shared_task(queue='high_priority')
def send_alert_notification(node_id=None):
    celery_logger.info(f"📧 Alert notification for node {node_id}")
    # TODO: Implement alert notification logic
    pass