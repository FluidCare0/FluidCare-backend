# sensor_app/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

class SensorConsumer(AsyncWebsocketConsumer):
    DEVICE_STATUS_CACHE_KEY = "device_status:{}"

    async def connect(self):
        self.room_group_name = 'sensor_monitoring'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'type': 'connection_established', 'message': 'Connected'}))
        logger.info(f"WebSocket connected to {self.room_group_name}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected from {self.room_group_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {text_data}")

    async def sensor_message(self, event):
        """Receive the final prepared message from the channel layer and send to WebSocket."""
        # The message here is the one prepared by the consumer itself after fetching status
        message_to_send = event['message'] # e.g., {'type': 'sensor_data', 'message': {..., 'status': '...'}}

        # Send the message directly
        await self.send(text_data=json.dumps(message_to_send))
        logger.debug(f"Sent to WebSocket: {message_to_send}")

    # --- NEW method to handle raw sensor data from Celery task via channel layer ---
    async def handle_sensor_data_from_task(self, event):
        """
        Receive raw sensor data from the Celery task via channel layer group.
        Fetch the status from Redis cache and broadcast the complete message.
        """
        # The 'event' contains the data sent by the Celery task via channel_layer.group_send
        # The Celery task sends: {'type': 'handle_sensor_data_from_task', 'sensor_data': {...}}
        raw_sensor_data = event.get('sensor_data')
        if not raw_sensor_data:
            logger.error(f"No 'sensor_data' found in event: {event}")
            return

        logger.info(f"Received raw sensor data from task for WebSocket processing: {raw_sensor_data}")

        # Get the device identifier from the raw data (nodeId or nodeMac)
        device_identifier = raw_sensor_data.get('nodeId') or raw_sensor_data.get('nodeMac')
        if not device_identifier:
            logger.error(f"No device identifier (nodeId or nodeMac) in raw sensor data: {raw_sensor_data}")
            return

        # --- Fetch Status from Redis Cache ---
        redis_client = redis.from_url(settings.REDIS_URL)
        try:
            # Adjust the cache key format according to your implementation
            cache_key = f"device_status:{device_identifier}"
            cached_status_bytes = redis_client.get(cache_key)
            # Default to 'Offline' if not found in cache, assuming it's not actively reporting
            cached_status = cached_status_bytes.decode('utf-8') if cached_status_bytes else 'Offline'
            logger.debug(f"Fetched cached status for {device_identifier}: {cached_status}")
        except redis.RedisError as e:
            logger.error(f"Error fetching status from Redis for {device_identifier}: {e}")
            cached_status = 'Offline' # Fallback status if cache fails
        finally:
            redis_client.close() # Ensure connection is closed

        # --- Prepare Final Message for Frontend ---
        # Include the fetched status in the message
        final_message_for_websocket = {
            'type': 'sensor_data',
            'message': {
                **raw_sensor_data, # Include all data from the Celery task (level, battery, etc.)
                'status': cached_status # Add the status fetched from cache
            }
        }

        logger.debug(f"Prepared final message for WebSocket (with status): {final_message_for_websocket}")

        # --- Broadcast Final Message via Channel Layer to WebSocket ---
        # This calls the 'sensor_message' handler which sends to the WebSocket
        await self.channel_layer.group_send(
            self.room_group_name, # Group name where connected WebSockets are listening
            {
                'type': 'sensor_message', # Route to the sensor_message handler which sends to WS
                'message': final_message_for_websocket
            }
        )
        logger.info(f"Broadcasted final sensor data with status via channel layer for device {device_identifier}")
