import logging
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from sensor_app.models import Device, FluidBag, SensorReading
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

CACHE_TIMEOUT = 60 * 10 

mqtt_logger = logging.getLogger('mqtt')
django_logger = logging.getLogger('django')


def get_bed_info(device):
    from survey_app.models import DeviceBedAssignmentHistory
    try:
        assignment = DeviceBedAssignmentHistory.objects.filter(
            device=device,
            end_time__isnull=True
        ).select_related('bed__ward__floor').first()
        
        if assignment:
            return {
                'bed_number': assignment.bed.bed_number,
                'ward_number': assignment.bed.ward.ward_number,
                'ward_name': assignment.bed.ward.name,
                'floor_number': assignment.bed.ward.floor.floor_number,
            }
    except Exception as e:
        django_logger.error(f"Error getting bed info: {e}")
    
    return None


def parse_datetime(datetime_str):
    """
    Parse multiple datetime formats safely for IoT payloads.
    Handles both backend and device formats.
    """
    possible_formats = [
        "%Y-%m-%d %H:%M:%S",        # Device format
        "%b. %d, %Y, %I:%M:%S %p",  # Backend format
        "%b %d, %Y, %I:%M:%S %p",   # Variant (no dot)
        "%Y-%m-%dT%H:%M:%S",        # ISO fallback
    ]
    
    for fmt in possible_formats:
        try:
            parsed = datetime.strptime(datetime_str, fmt)
            if fmt != possible_formats[0]:
                mqtt_logger.warning(f"⚠️ Parsed datetime with fallback format '{fmt}': {datetime_str}")
            return parsed
        except ValueError:
            continue

    raise ValueError(f"Unsupported datetime format: {datetime_str}")


def handle_node_id_request(self, topic, payload):
    """Handles Node ID request and forwards only MAC to WebSocket"""
    try:
        mac_address = payload.get("mac")
        if not mac_address:
            mqtt_logger.warning(f"⚠️ No MAC address found in payload: {payload}")
            return

        mqtt_logger.info(f"📨 Node ID request received from MAC: {mac_address}")

        async_to_sync(self.channel_layer.group_send)(
            "sensor_monitoring",
            {
                "type": "node_id_request",
                "mac": mac_address,
            }
        )

        mqtt_logger.info(f"📤 Node ID request (MAC: {mac_address}) forwarded to WebSocket")

    except Exception as e:
        mqtt_logger.error(f"❌ Failed to handle Node ID request: {e}", exc_info=True)
