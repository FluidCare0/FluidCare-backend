import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.auth import login

class SensorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
        else:
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
            
            # Subscribe to specific floor
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
            
            # Unsubscribe from specific floor
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