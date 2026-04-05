import json
import uuid
import time
import logging
import redis
from datetime import timedelta

from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.conf import settings
from django.db import transaction, DatabaseError
from django.utils import timezone

from notification_app.models import Notification
from notification_app.tasks import create_notification, send_notification_to_websocket
from sensor_app.models import Device, FluidBag, SensorReading, PatientDeviceBedAssignment
from sensor_app.utils import parse_datetime

# Redis connection
r = redis.Redis.from_url(settings.REDIS_URL)

# Celery logger
celery_logger = logging.getLogger('celery')

# Cache key constants
DEVICE_STATUS_CACHE_KEY = "device_status:{}"
DEVICE_LAST_SEEN_CACHE_KEY = "device_last_seen:{}"
OFFLINE_THRESHOLD_SECONDS = 120  # 2 minutes

QUEUE_KEY = "sensor_queue"
LOCK_KEY = "sensor_batch_lock"
DEBOUNCE_KEY = "sensor_batch_debounce"
BATCH_SIZE = 1000  # Threshold to trigger immediate processing
MAX_BATCH_PROCESS = 5000  # Maximum items to process per periodic run


# ============================================
# HELPER FUNCTIONS
# ============================================

def acquire_lock(lock_key, timeout=15):
    """Acquire a Redis lock"""
    return r.set(lock_key, "1", nx=True, ex=timeout)


def release_lock(lock_key):
    """Release a Redis lock"""
    r.delete(lock_key)


def update_device_status(device_id):
    """
    Update device status in both cache and database.
    Marks device as active/online.
    """
    try:
        # Update last_seen in database
        Device.objects.filter(id=device_id).update(
            last_seen=timezone.now()
        )

        # Update status in Redis cache to 'Activate'
        cache_key_status = DEVICE_STATUS_CACHE_KEY.format(device_id)
        r.setex(cache_key_status, OFFLINE_THRESHOLD_SECONDS + 60, "Activate")

        # Update last seen timestamp in Redis cache
        cache_key_last_seen = DEVICE_LAST_SEEN_CACHE_KEY.format(device_id)
        r.setex(cache_key_last_seen, OFFLINE_THRESHOLD_SECONDS + 60, int(time.time()))

        # Update DB status to 'online' if it wasn't already
        device = Device.objects.get(id=device_id)
        if device.status != 'online':
            Device.objects.filter(id=device_id).update(status='online')
            celery_logger.info(f"✅ Device {device_id} status updated to online")

    except Device.DoesNotExist:
        celery_logger.warning(f"⚠️ Device {device_id} not found")
    except redis.RedisError as e:
        celery_logger.error(f"❌ Redis error for device {device_id}: {e}")


def send_sensor_data_to_websocket(sensor_payload):
    try:
        channel_layer = get_channel_layer()

        if channel_layer:
            # Send to WebSocket group
            async_to_sync(channel_layer.group_send)(
                "sensor_monitoring",
                {
                    "type": "handle_sensor_data_from_task",
                    "sensor_data": sensor_payload
                }
            )
            celery_logger.debug(f"📡 Sent WebSocket update for node {sensor_payload.get('nodeId')}")
        else:
            celery_logger.warning("⚠️ Channel layer is not available. Cannot send WebSocket message.")

    except Exception as e:
        celery_logger.error(f"❌ WebSocket send error: {e}", exc_info=True)

@shared_task(bind=True, max_retries=3, default_retry_delay=2, queue="celery")
def process_sensor_data(self, payload):
    node_id_str = payload.get('node_id')

    if not node_id_str:
        celery_logger.error(f"❌ No 'node_id' found in payload: {payload}")
        return "NO_NODE_ID"

    try:
        node_id = uuid.UUID(node_id_str)
    except ValueError:
        celery_logger.error(f"❌ Invalid 'node_id' format: {node_id_str}")
        return "INVALID_NODE_ID"

    # Update device status (last_seen, etc.)
    try:
        device = Device.objects.get(id=node_id)
        update_device_status(device.id)
    except Device.DoesNotExist:
        celery_logger.warning(f"⚠️ Device with ID {node_id} not found in database. Message: {payload}")
        return "DEVICE_NOT_FOUND"

    reading_value = payload.get("reading")
    if reading_value is None:
        celery_logger.warning(f"⚠️ No 'reading' field in payload: {payload}")
        return "NO_READING"

    datetime_str = payload.get("datetime")
    if not datetime_str:
        celery_logger.error(f"❌ No 'datetime' found in payload: {payload}")
        return "NO_DATETIME"

    try:
        ts = parse_datetime(datetime_str)
    except Exception as e:
        celery_logger.error(f"❌ Error parsing datetime '{datetime_str}': {e}")
        return "DATETIME_PARSE_ERROR"

    try:
        r.lpush(QUEUE_KEY, json.dumps(payload))
        queue_len = r.llen(QUEUE_KEY)
        celery_logger.debug(f"📥 Added message to queue. Current queue length: {queue_len}")

        if queue_len >= BATCH_SIZE:
            celery_logger.info(f"🚀 Queue length ({queue_len}) reached threshold, triggering batch task")
            trigger_batch_task()

    except redis.RedisError as e:
        celery_logger.error(f"❌ Redis error adding to queue: {e}")
        try:
            save_single_reading_to_db(payload, node_id, ts)
        except Exception as db_e:
            celery_logger.error(f"❌ Fallback DB save also failed: {db_e}")
            raise

    return "SUCCESS"


def save_single_reading_to_db(payload, node_id, timestamp):
  
    fluid_bag = FluidBag.objects.filter(device_id=node_id).first()
    if not fluid_bag:
        celery_logger.warning(f"⚠️ FluidBag not found for device {node_id}")
        return

    reading_value = payload.get("reading")
    if reading_value is None:
        return

    with transaction.atomic():
        SensorReading.objects.create(
            fluid_bag=fluid_bag,
            reading=int(reading_value),
            smoothed_weight=payload.get("smoothed_weight"),
            timestamp=timestamp,
            via=bool(payload.get("via")),
            battery_percent=payload.get("battery_percent"),
            repeater_mac=payload.get("repeater_mac"),
            master_mac=payload.get("master_mac"),
        )
    celery_logger.info(f"✅ Fallback: Saved single reading for device {node_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue="celery")
def process_sensor_batch(self):
    celery_logger.info("📦 Starting batch processing...")

    if not acquire_lock(LOCK_KEY, timeout=20):
        celery_logger.info("🔒 Lock already acquired, skipping this run")
        return "LOCKED"

    try:
        queue_len = r.llen(QUEUE_KEY)
        celery_logger.info(f"📊 Current queue length: {queue_len}")

        if queue_len == 0:
            celery_logger.info("🔭 No data in queue")
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
            celery_logger.info("🔭 No valid data in queue after parsing")
            return "NO_VALID_DATA"

        node_ids = {uuid.UUID(item["node_id"]) for item in batch}
        devices = Device.objects.filter(id__in=node_ids).in_bulk(field_name="id")

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

                datetime_str = msg.get("datetime")
                if not datetime_str:
                    celery_logger.warning(f"⚠️ No 'datetime' in message: {msg}")
                    errors += 1
                    continue

                try:
                    ts = parse_datetime(datetime_str)
                except Exception as e:
                    celery_logger.error(f"❌ Error parsing datetime '{datetime_str}': {e}")
                    errors += 1
                    continue

                reading_value = msg.get("reading")
                if reading_value is None:
                    celery_logger.warning(f"⚠️ No 'reading' field in message: {msg}")
                    errors += 1
                    continue

                readings_to_insert.append(
                    SensorReading(
                        fluid_bag=fluid_bag,
                        reading=int(reading_value),
                        smoothed_weight=msg.get("smoothed_weight"),
                        timestamp=ts,
                        via=bool(msg.get("via")),
                        battery_percent=msg.get("battery_percent"),
                        repeater_mac=msg.get("repeater_mac"),
                        master_mac=msg.get("master_mac"),
                    )
                )

                # --- Check for Low Fluid Level Threshold (use smoothed if available) ---
                alert_value = msg.get("smoothed_weight") or int(reading_value)
                if fluid_bag.threshold_low and alert_value <= fluid_bag.threshold_low:
                        # Only create a notification if one doesn't exist for this device in the last 30 mins
                        recent_notif = Notification.objects.filter(
                            device=device,
                            notification_type='warning',
                            created_at__gte=timezone.now() - timedelta(minutes=30)
                        ).exists()
                        
                        if not recent_notif:
                            create_notification(
                                device=device,
                                title="IV Bottle Low",
                                message=f"Fluid level for patient {fluid_bag.device.current_assignment.patient.name if fluid_bag.device.current_assignment and fluid_bag.device.current_assignment.patient else 'Unknown'} is at {reading_value}%.",
                                n_type='warning',
                                severity='med'
                            )


            except Exception as msg_error:
                celery_logger.error(f"❌ Error processing message {msg}: {msg_error}")
                errors += 1

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
    if not r.exists(DEBOUNCE_KEY):
        r.set(DEBOUNCE_KEY, "1", ex=2)  # Debounce for 2 seconds
        celery_logger.info("🚀 Manually triggering batch task")
        process_sensor_batch.delay()
    else:
        celery_logger.debug("⏸️ Batch task debounced")




@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue="celery")
def process_task_completion(self, payload):
    node_id_str = payload.get('node_id')
    if not node_id_str:
        celery_logger.error(f"❌ No 'node_id' found in task completion payload: {payload}")
        return "NO_NODE_ID"

    try:
        node_id = uuid.UUID(node_id_str)
    except ValueError:
        celery_logger.error(f"❌ Invalid 'node_id' format in task completion payload: {node_id_str}")
        return "INVALID_NODE_ID"

    try:
        device = Device.objects.get(id=node_id)

        Device.objects.filter(id=device.id).update(
            status='completed'
        )

        assignment = PatientDeviceBedAssignment.objects.filter(device=device, end_time__isnull=True).first()
        if assignment:
            assignment.end_time = timezone.now()
            assignment.save()
            if assignment.bed:
                assignment.bed.is_occupied = False
                assignment.bed.save(update_fields=['is_occupied'])

        cache_key_status = DEVICE_STATUS_CACHE_KEY.format(device.id)
        r.setex(cache_key_status, 600, "Task_Completed")

        celery_logger.info(f"✅ Device {device.id} marked as task-completed (stop_at set, status=False)")

        send_sensor_data_to_websocket({
            'nodeId': node_id_str,
            'status': 'Task_Completed',
            'timestamp': timezone.now().isoformat()
        })

    except Device.DoesNotExist:
        celery_logger.warning(f"⚠️ Device {node_id} not found for task completion")
        return "DEVICE_NOT_FOUND"
    except redis.RedisError as e:
        celery_logger.error(f"❌ Redis error during task completion for device {node_id}: {e}")

    return "TASK_COMPLETED"


@shared_task(bind=True, max_retries=3, default_retry_delay=5, queue="celery")
def process_disconnect(self, payload):
    node_id_str = payload.get('node_id')
    if not node_id_str:
        celery_logger.error(f"❌ No 'node_id' found in disconnect payload: {payload}")
        return "NO_NODE_ID"
    try:
        node_id = uuid.UUID(node_id_str)
    except ValueError:
        celery_logger.error(f"❌ Invalid 'node_id' format in disconnect payload: {node_id_str}")
        return "INVALID_NODE_ID"
    try:
        device = Device.objects.get(id=node_id)

        Device.objects.filter(id=device.id).update(
            status='offline'
        )

        assignment = PatientDeviceBedAssignment.objects.filter(device=device, end_time__isnull=True).first()
        if assignment:
            assignment.end_time = timezone.now()
            assignment.save()
            if assignment.bed:
                assignment.bed.is_occupied = False
                assignment.bed.save(update_fields=['is_occupied'])

        cache_key_status = DEVICE_STATUS_CACHE_KEY.format(device.id)
        r.setex(cache_key_status, 600, "Offline")

        celery_logger.info(f"✅ Device {device.id} marked as disconnected (stop_at set, status=False)")

        send_sensor_data_to_websocket({
            'nodeId': node_id_str,
            'status': 'Offline',
            'timestamp': timezone.now().isoformat()
        })

    except Device.DoesNotExist:
        celery_logger.warning(f"⚠️ Device {node_id} not found for disconnect")
        return "DEVICE_NOT_FOUND"
    except redis.RedisError as e:
        celery_logger.error(f"❌ Redis error during disconnect for device {node_id}: {e}")

    return "DISCONNECTED"


@shared_task(queue="celery")
def check_device_connectivity():
    celery_logger.info("🔍 Starting connectivity check task...")
    threshold_time = int(time.time()) - OFFLINE_THRESHOLD_SECONDS

    active_not_stopped_devices = Device.objects.filter(
        status='online'
    ).values_list('id', flat=True)

    offline_devices_count = 0

    for device_id in active_not_stopped_devices:
        cache_key_last_seen = DEVICE_LAST_SEEN_CACHE_KEY.format(device_id)
        try:
            last_seen_bytes = r.get(cache_key_last_seen)
            
            if last_seen_bytes:
                last_seen_timestamp = int(last_seen_bytes)
                
                if last_seen_timestamp < threshold_time:
                    # Device is offline due to inactivity
                    Device.objects.filter(
                        id=device_id,
                        status='online'
                    ).update(status='offline')

                    # Update Redis status cache to 'Offline'
                    cache_key_status = DEVICE_STATUS_CACHE_KEY.format(device_id)
                    r.setex(cache_key_status, 600, "Offline")

                    celery_logger.info(
                        f"⚠️ Device {device_id} marked as offline "
                        f"(last seen {last_seen_timestamp}, threshold {threshold_time})"
                    )
                    offline_devices_count += 1

                    # Create Notification
                    create_notification(
                        device=Device.objects.get(id=device_id),
                        title="Device Offline",
                        message=f"Device {device_id} has gone offline due to inactivity.",
                        n_type='error',
                        severity='high'
                    )

                    # Send WebSocket notification about offline status
                    send_sensor_data_to_websocket({
                        'nodeId': str(device_id),
                        'status': 'Offline',
                        'reason': 'Inactivity timeout',
                        'timestamp': timezone.now().isoformat()
                    })
            else:
                # No last seen timestamp in cache for an active device
                celery_logger.warning(
                    f"⚠️ Device {device_id} has no last_seen timestamp in cache "
                    f"but DB status is True. Marking offline..."
                )

                Device.objects.filter(
                    id=device_id,
                    status='online'
                ).update(status='offline')

                cache_key_status = DEVICE_STATUS_CACHE_KEY.format(device_id)
                r.setex(cache_key_status, 600, "Offline")
                offline_devices_count += 1

        except ValueError:
            celery_logger.error(f"❌ Invalid last_seen timestamp format for device {device_id}")
        except redis.RedisError as e:
            celery_logger.error(f"❌ Redis error checking device {device_id}: {e}")

    celery_logger.info(
        f"✅ Connectivity check completed. "
        f"{offline_devices_count} devices marked as offline due to inactivity."
    )

