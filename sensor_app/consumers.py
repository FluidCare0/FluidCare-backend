# sensor_app/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.auth import login
from django.contrib.auth.models import AnonymousUser

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Optional: Add authentication logic here if needed beyond the ASGI middleware
        # if isinstance(self.scope["user"], AnonymousUser):
        #     await self.close()
        # else:
        self.room_group_name = 'sensor_monitoring'

        # Join general monitoring group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to sensor monitoring'
        }))

    async def disconnect(self, close_code):
        # Leave general monitoring group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            # Subscribe to specific floor (optional feature)
            if message_type == 'subscribe_floor':
                floor_number = text_data_json.get('floor')
                if floor_number:
                    await self.channel_layer.group_add(
                        f'floor_{floor_number}',
                        self.channel_name
                    )
                    await self.send(text_data=json.dumps({
                        'type': 'subscription_confirmed',
                        'floor': floor_number
                    }))

            # Unsubscribe from specific floor (optional feature)
            elif message_type == 'unsubscribe_floor':
                floor_number = text_data_json.get('floor')
                if floor_number:
                    await self.channel_layer.group_discard(
                        f'floor_{floor_number}',
                        self.channel_name
                    )

        except json.JSONDecodeError:
            pass

    async def sensor_message(self, event):
        """Receive message from group and send to WebSocket"""
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))

    # --- New method to handle messages from Celery ---
    async def handle_sensor_data(self, sensor_data):
        """
        This method is called from your Celery task or wherever you process the MQTT message.
        It sends the sensor data to the 'sensor_monitoring' group.
        """
        # Example: Prepare the message structure expected by the frontend
        # The sensor_data is the payload from MQTT (e.g., {'node_id': ..., 'reading': ...})
        message_to_send = {
            'type': 'sensor_data', # Identify the message type
            'message': sensor_data # The actual sensor data payload
        }

        # Send the message to the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'sensor_message', # Route to the sensor_message handler
                'message': message_to_send
            }
        )
    # --- End of new method ---
