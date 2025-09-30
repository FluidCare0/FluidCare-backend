import json 
import logging
import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from sensor_app.models import Device, FluidBag, SensorReading
from sensor_app.utils import process_mqtt_message, get_bed_info

mqtt_logger = logging.getLogger('mqtt')

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.channel_layer = get_channel_layer()

        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
    def broadcast_sensor_update(self, sensor_reading, mqtt_data):
        try:
            bed_info = get_bed_info(sensor_reading.fluidBag.device)
            
            message = {
                'type': 'sensor_update',
                'data': {
                    'node_id': mqtt_data.get('node_id'),
                    'device_id': sensor_reading.fluidBag.device.mac_address,
                    'fluid_bag_type': sensor_reading.fluidBag.type,
                    'fluid_level': sensor_reading.fluid_level,
                    'status': sensor_reading.status,
                    'timestamp': sensor_reading.timestamp.isoformat(),
                    'floor': mqtt_data.get('floor'),
                    'bed_info': bed_info,
                }
            }
            
            # Send to general monitoring group
            async_to_sync(self.channel_layer.group_send)( # type: ignore
                'sensor_monitoring',
                {
                    'type': 'sensor_message',
                    'message': message
                }
            )
            
            # Send to floor-specific group if floor exists
            if mqtt_data.get('floor'):
                async_to_sync(self.channel_layer.group_send)( # type: ignore
                    f'floor_{mqtt_data.get("floor")}',
                    {
                        'type': 'sensor_message',
                        'message': message
                    }
                )
            
            mqtt_logger.info(f"Broadcast sensor update for node {mqtt_data.get('node_id')}")
            
        except Exception as e:
            mqtt_logger.error(f"Error broadcasting sensor update: {e}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            mqtt_logger.info('Mqtt broker connected')
            client.subscribe(settings.MQTT_TOPIC, qos=1)
            mqtt_logger.info(f'Subscribed to topic: {settings.MQTT_TOPIC}')
        else:
            mqtt_logger.error(f'Failed to connect, return code {rc}')

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            mqtt_logger.warning("Unexpected MQTT disconnection. Reconnecting...")  

    def on_message(self, client, userdata, msg):
        try:
            # Parse MQTT message
            payload = json.loads(msg.payload.decode())
            mqtt_logger.info(f"Received message: {payload}")
            
            # Process the sensor data
            sensor_reading = process_mqtt_message(payload)
            
            if sensor_reading:
                # Send update via WebSocket to connected clients
                self.broadcast_sensor_update(sensor_reading, payload)
                
        except json.JSONDecodeError:
            mqtt_logger.error(f"Invalid JSON in MQTT message: {msg.payload}")
        except Exception as e:
            mqtt_logger.error(f"Error processing MQTT message: {e}")

        
    def connect(self):
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            mqtt_logger.info('MQTT Client Started')
        except Exception as e:
            mqtt_logger.error(f'Failed to connect to mqtt broker')

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
        mqtt_logger.info("MQTT Client disconnected")

mqtt_client = None

def get_mqtt_client():
    global mqtt_client
    if mqtt_client is None:
        mqtt_client = MQTTClient()
        mqtt_client.connect()
    return mqtt_client
        