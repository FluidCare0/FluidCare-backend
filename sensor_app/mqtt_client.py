# sensor_app/mqtt_client.py
import json 
import logging
import os
import paho.mqtt.client as mqtt
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import redis
from sensor_app.models import Device, FluidBag, SensorReading
from sensor_app.tasks import trigger_batch_task, process_sensor_data, process_task_completion, process_disconnect
from sensor_app.utils import handle_node_id_request, handle_node_reset_request
import ssl
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

        ca_cert_path = os.path.join(settings.BASE_DIR, "sensor_app", "certs", "isrgrootx1.pem")
        self.client.tls_set(
            ca_certs=ca_cert_path,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT
        )
        self.client.tls_insecure_set(False)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            mqtt_logger.info('Mqtt broker connected')
            client.subscribe(settings.MQTT_TOPIC, qos=1)
            task_complete_topic = settings.MQTT_TASK_COMPLETE_TOPIC # Define this in your Django settings
            if task_complete_topic:
                client.subscribe(task_complete_topic, qos=1)
                mqtt_logger.info(f'Subscribed to task completion topic: {task_complete_topic}')
            # Subscribe to node reset requests from master
            client.subscribe('be_project/node/reset', qos=1)
            mqtt_logger.info('Subscribed to: be_project/node/reset')
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

            if 'be_project/node/data' in topic and 'be_project/task_complete' not in topic and 'be_project/disconnect' not in topic: # Regular data topic (adjust pattern as needed)
                result = process_sensor_data.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Sensor processing task queued with ID: {result.id} for topic {topic}")

                r.lpush(QUEUE_KEY, json.dumps(payload))
                queue_len = r.llen(QUEUE_KEY)
                mqtt_logger.info(f"📊 Queue length for batch: {queue_len}")

                if queue_len >= BATCH_SIZE: # type: ignore
                    mqtt_logger.info(f"🎯 Batch size reached ({queue_len} >= {BATCH_SIZE}), triggering batch")
                    trigger_batch_task()
                else:
                    mqtt_logger.debug(f"⏳ Waiting for batch ({queue_len}/{BATCH_SIZE})")

            elif 'be_project/task_complete' in topic: # Task completion topic (adjust pattern as needed)
                result = process_task_completion.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Task completion processing task queued with ID: {result.id} for topic {topic}")

            elif 'be_project/disconnect' in topic: # Disconnect topic (adjust pattern as needed)
                result = process_disconnect.delay(payload) # type: ignore
                mqtt_logger.info(f"✅ Disconnect processing task queued with ID: {result.id} for topic {topic}")

            elif 'be_project/node/request/id' in topic:
                topic = msg.topic
                payload = json.loads(msg.payload.decode())
                handle_node_id_request(self, topic, payload)

            elif 'be_project/node/reset' in topic:
                handle_node_reset_request(self, topic, payload)
                mqtt_logger.info(f"✅ Node reset request handled for topic {topic}")

            
        
        except json.JSONDecodeError as je:
            mqtt_logger.error(f"❌ Invalid JSON in MQTT message: {msg.payload}, Error: {je}")

        except Exception as e:
            mqtt_logger.error(f'❌ Error in on_message: {e}', exc_info=True)
                 
    def connect(self):
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()
            mqtt_logger.info('✅ Secure MQTT Client Started with TLS')
        except Exception as e:
            mqtt_logger.error(f'Failed to connect to MQTT broker: {e}')

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

def publish_message(topic: str, payload: dict, qos: int = 1, retain: bool = False):
    try:
        client = get_mqtt_client()
        json_payload = json.dumps(payload)

        mqtt_logger.info(f"📤 JSON being published to '{topic}': {json_payload}")

        result = client.client.publish(topic, json_payload, qos=qos, retain=retain)

        if result.rc == 0:
            mqtt_logger.info(f"✅ Published message to '{topic}' successfully.")
        else:
            mqtt_logger.error(f"❌ Failed to publish message to '{topic}', result code: {result.rc}")

    except Exception as e:
        mqtt_logger.error(f"❌ Error while publishing to MQTT: {e}", exc_info=True)
