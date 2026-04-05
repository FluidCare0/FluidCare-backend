# sensor_app/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
import redis
from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from sensor_app.models import PatientDeviceBedAssignment
from hospital_app.models import Patient, Floor
from sensor_app.serializers import PatientDeviceBedAssignmentSerializer
from hospital_app.serializers import PatientListWithLocationSerializer, FloorSerializer

logger = logging.getLogger(__name__)

class SensorConsumer(AsyncWebsocketConsumer):
    DEVICE_STATUS_CACHE_KEY = "device_status:{}"

    async def connect(self):
        self.room_group_name = 'sensor_monitoring'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({'type': 'connection_established', 'message': 'Connected'}))
        logger.info(f"WebSocket connected to {self.room_group_name}")
        
        # Send initial data
        initial_data = await self.get_initial_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'data': initial_data
        }))
        logger.info("Sent initial data to WebSocket")

    @sync_to_async
    def get_initial_data(self):
        # 1. Devices (Active Assignments)
        active_assignments = (
            PatientDeviceBedAssignment.objects
            .filter(end_time__isnull=True, device__isnull=False)
            .select_related('patient', 'device', 'bed', 'ward', 'floor')
        )
        devices_data = PatientDeviceBedAssignmentSerializer(active_assignments, many=True).data

        # 2. Admitted Patients
        patients = Patient.objects.filter(
            discharged_at__isnull=True
        ).prefetch_related('assignments__bed__ward__floor')
        # Filter for patients who have an active assignment (equivalent to p.floor && p.ward && p.bed in frontend)
        # However, the frontend might want all admitted patients for the selection modal.
        # Let's send all non-discharged patients.
        patients_data = PatientListWithLocationSerializer(patients, many=True).data

        # 3. Hospital Structure
        floors = Floor.objects.all().prefetch_related('wards__beds')
        structure_data = FloorSerializer(floors, many=True).data

        return {
            'devices': devices_data,
            'patients': patients_data,
            'hospitalStructure': structure_data
        }

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
        # The message here is the one prepared by the consumer itself after fetching status
        message_to_send = event['message'] # e.g., {'type': 'sensor_data', 'message': {..., 'status': '...'}}

        # Send the message directly
        await self.send(text_data=json.dumps(message_to_send))
        logger.debug(f"Sent to WebSocket: {message_to_send}")

    async def node_id_request(self, event):
        mac_address = event.get("mac")

        if not mac_address:
            logger.warning(f"No MAC found in node_id_request event: {event}")
            return

        message = {
            "type": "node_id_request",
            "mac": mac_address,
        }

        # Send directly to frontend WebSocket
        await self.send(text_data=json.dumps(message))
        logger.info(f"📤 Sent Node ID request MAC to WebSocket: {mac_address}")

    async def handle_sensor_data_from_task(self, event):
        raw_sensor_data = event.get('sensor_data')
        if not raw_sensor_data:
            logger.error(f"No 'sensor_data' found in event: {event}")
            return

        logger.info(f"Received raw sensor data from task for WebSocket processing: {raw_sensor_data}")

        device_identifier = raw_sensor_data.get('nodeId') or raw_sensor_data.get('nodeMac')
        if not device_identifier:
            logger.error(f"No device identifier (nodeId or nodeMac) in raw sensor data: {raw_sensor_data}")
            return

        redis_client = redis.from_url(settings.REDIS_URL)
        try:
            cache_key = f"device_status:{device_identifier}"
            cached_status_bytes = redis_client.get(cache_key)
            cached_status = cached_status_bytes.decode('utf-8') if cached_status_bytes else 'Offline'
            logger.debug(f"Fetched cached status for {device_identifier}: {cached_status}")
        except redis.RedisError as e:
            logger.error(f"Error fetching status from Redis for {device_identifier}: {e}")
            cached_status = 'Offline' 
        finally:
            redis_client.close() 

        final_message_for_websocket = {
            'type': 'sensor_data',
            'message': {
                **raw_sensor_data, 
                'status': cached_status 
            }
        }

        logger.debug(f"Prepared final message for WebSocket (with status): {final_message_for_websocket}")

        await self.channel_layer.group_send(
            self.room_group_name, 
            {
                'type': 'sensor_message', 
                'message': final_message_for_websocket
            }
        )
        logger.info(f"Broadcasted final sensor data with status via channel layer for device {device_identifier}")

    async def handle_notification(self, event):
        notification_data = event.get('notification')
        if notification_data:
            await self.send(text_data=json.dumps({
                'type': 'new_notification',
                'notification': notification_data
            }))
            logger.info(f"🔔 Dispatched new notification to WebSocket: {notification_data.get('title')}")

    async def refresh_notifications(self, event):
        await self.send(text_data=json.dumps({
            'type': 'refresh_notifications'
        }))
        logger.info("🔄 Dispatched refresh_notifications to WebSocket")
