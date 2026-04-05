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


def handle_node_reset_request(mqtt_client_instance, topic, payload):
    """
    Handles a Node Reset Request (203).

    Flow:
      1. Extract MAC (and optional node_id) from the MQTT payload.
      2. Delete the Device record identified by that MAC — this removes the
         Node-ID from the backend database.
      3. Publish a 204 Reset ACK back to be_project/node/reset/ack so the
         master can forward it to the requesting node.
    """
    from sensor_app.mqtt_client import publish_message

    try:
        mac_address = payload.get("mac")
        if not mac_address:
            mqtt_logger.warning(f"⚠️ No MAC address in reset payload: {payload}")
            return

        mqtt_logger.info(f"🔄 Reset request (203) received from MAC: {mac_address}")

        # ---- Delete the Device record (this removes the Node-ID) -------------
        deleted_count, _ = Device.objects.filter(
            mac_address__iexact=mac_address,
            type="node"
        ).delete()

        if deleted_count:
            mqtt_logger.info(f"🗑️  Device deleted for MAC: {mac_address} ({deleted_count} record(s))")
        else:
            mqtt_logger.warning(f"⚠️  No Device found for MAC: {mac_address} — sending ACK anyway")

        # ---- Send 204 Reset ACK back to the master ---------------------------
        ack_payload = {
            "request_code": 204,   # RES_RESET_ACK
            "mac": mac_address,
        }
        publish_message("be_project/node/reset/ack", ack_payload)
        mqtt_logger.info(f"📤 Reset ACK (204) published for MAC: {mac_address}")

    except Exception as e:
        mqtt_logger.error(f"❌ Failed to handle Node Reset request: {e}", exc_info=True)

