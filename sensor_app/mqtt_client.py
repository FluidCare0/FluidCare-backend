# sensor_app/mqtt_client.py
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
from sensor_app.tasks import trigger_batch_task, process_sensor_data, process_task_completion, process_disconnect
# Update imports to use the new tasks

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
            # Subscribe to the task completion topic
            # Adjust the topic pattern as needed
            task_complete_topic = settings.MQTT_TASK_COMPLETE_TOPIC # Define this in your Django settings
            if task_complete_topic:
                client.subscribe(task_complete_topic, qos=1)
                mqtt_logger.info(f'Subscribed to task completion topic: {task_complete_topic}')
        else:
            mqtt_logger.error(f'Failed to connect, return code {rc}')

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            mqtt_logger.warning("Unexpected MQTT disconnection. Reconnecting...")  

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            mqtt_logger.info(f"📨 Received message on topic '{topic}': {payload}")

            if 'be_project/node_' in topic and 'be_project/task_complete' not in topic and 'be_project/disconnect' not in topic: # Regular data topic (adjust pattern as needed)
                # --- CALL THE TASK FOR REGULAR DATA ---
                # This task handles status update, DB save, and WebSocket send for regular data
                result = process_sensor_data.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Sensor processing task queued with ID: {result.id} for topic {topic}")
                # --- END CALL ---

                # --- QUEUE FOR BATCH PROCESSING (if you still need it for historical data) ---
                r.lpush(QUEUE_KEY, json.dumps(payload))
                queue_len = r.llen(QUEUE_KEY)
                mqtt_logger.info(f"📊 Queue length for batch: {queue_len}")

                if queue_len >= BATCH_SIZE: # type: ignore
                    mqtt_logger.info(f"🎯 Batch size reached ({queue_len} >= {BATCH_SIZE}), triggering batch")
                    trigger_batch_task()
                else:
                    mqtt_logger.debug(f"⏳ Waiting for batch ({queue_len}/{BATCH_SIZE})")

            elif 'be_project/task_complete' in topic: # Task completion topic (adjust pattern as needed)
                # --- CALL THE TASK FOR TASK COMPLETION ---
                # This task handles setting stop_at and status for task completion
                result = process_task_completion.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Task completion processing task queued with ID: {result.id} for topic {topic}")
                # --- END CALL ---

            elif 'be_project/disconnect' in topic: # Disconnect topic (adjust pattern as needed)
                # --- CALL THE TASK FOR DISCONNECT ---
                # This task handles setting status to False and stop_at
                result = process_disconnect.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Disconnect processing task queued with ID: {result.id} for topic {topic}")
                # --- END CALL ---

            elif 'be_project/request_uuid_' in topic:
                mqtt_logger.warning(f'TOPIC: {topic}')
            
        
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