from sensor_app.models import Device, FluidBag
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

mqtt_logger = logging.getLogger('mqtt')

CACHE_TIMEOUT = 60 * 10 

def get_device(node_id):
    key = f'device:{node_id}'
    device = cache.get(key)
    if device is None:
        device = Device.objects.get(id=node_id, type='node')
        cache.set(key, device, CACHE_TIMEOUT)
    return device

def get_fluid_bag(device):
    key = f'fluidbag:{device.id}'
    fluid_bag = cache.get(key)
    if fluid_bag is None:
        fluid_bag = FluidBag.objects.filter(device=device).first()
        cache.set(key, fluid_bag, CACHE_TIMEOUT)
    return fluid_bag


def send_sensor_data_to_websocket(sensor_payload):
    """
    Sends sensor data to the 'sensor_monitoring' WebSocket group.

    Args:
        sensor_payload (dict): The sensor data payload (e.g., from MQTT).
                               Example: {'node_id': '...', 'reading': 21.93, ...}
    """
    try:
        # Get the default channel layer configured in your Django settings
        channel_layer = get_channel_layer()

        if channel_layer:
            # Prepare the message structure for the WebSocket
            message_to_send = {
                'type': 'sensor_data',  # Identify the message type for the frontend
                'message': sensor_payload  # The actual sensor data
            }

            # Use async_to_sync to call the async channel_layer.group_send from sync code (like Celery task)
            async_to_sync(channel_layer.group_send)(
                "sensor_monitoring",  # The group name defined in SensorConsumer
                {
                    "type": "sensor_message",  # The consumer method to handle the message
                    "message": message_to_send
                }
            )
            mqtt_logger.info(f"WebSocket message sent for node {sensor_payload.get('node_id')}: {sensor_payload}")
        else:
            mqtt_logger.warning("Channel layer is not available. Cannot send WebSocket message.")

    except Exception as e:
        mqtt_logger.error(f"Error sending sensor data to WebSocket: {e}", exc_info=True)