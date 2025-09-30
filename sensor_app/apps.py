from django.apps import AppConfig


class SensorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sensor_app'

    def ready(self):
        import os
        
        if os.environ.get('RUN_MAIN') == 'true' or os.environ.get('RUN_MAIN') is None:
            from sensor_app.mqtt_client import get_mqtt_client
            
            try:
                get_mqtt_client()
            except Exception as e:
                print(f"Failed to start MQTT client: {e}")