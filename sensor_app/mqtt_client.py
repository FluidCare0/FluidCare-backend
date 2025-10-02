import json 
import logging
import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import redis
from sensor_app.models import Device, FluidBag, SensorReading
from sensor_app.tasks import process_alert, trigger_batch_task
from sensor_app.utils import process_mqtt_message, get_bed_info

r = redis.Redis.from_url(settings.REDIS_URL)
QUEUE_KEY = "sensor_queue"
LOCK_KEY = "sensor_batch_lock"
DEBOUNCE_KEY = "sensor_batch_debounce"
BATCH_SIZE = 1000
CACHE_TIMEOUT = 60 * 50  

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
            mqtt_logger.info(f"📨 Received message: {payload}")

            # Trigger alert processing
            mqtt_logger.info(f"🔔 Calling process_alert for node: {payload.get('node_id')}")
            result = process_alert.delay(payload)
            mqtt_logger.info(f"✅ Alert task queued with ID: {result.id}")

            # Add to batch queue
            r.lpush(QUEUE_KEY, json.dumps(payload))
            queue_len = r.llen(QUEUE_KEY)
            mqtt_logger.info(f"📊 Queue length: {queue_len}")

            # Trigger batch if threshold reached
            if queue_len >= BATCH_SIZE:
                mqtt_logger.info(f"🎯 Batch size reached ({queue_len} >= {BATCH_SIZE}), triggering batch")
                trigger_batch_task()
            else:
                mqtt_logger.debug(f"⏳ Waiting for batch ({queue_len}/{BATCH_SIZE})")
        
        except json.JSONDecodeError as je:
            mqtt_logger.error(f"❌ Invalid JSON in MQTT message: {msg.payload}, Error: {je}")

        except Exception as e:
            mqtt_logger.error(f'❌ Error in on_message: {e}', exc_info=True)
            
        
    def connect(self):
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            mqtt_logger.info('MQTT Client Started')
        except Exception as e:
            mqtt_logger.error(f'Failed to connect to mqtt broker: {e}')

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