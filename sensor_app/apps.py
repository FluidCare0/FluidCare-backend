from django.apps import AppConfig


class SensorAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sensor_app'

    def ready(self) -> None:
        from sensor_app.mqtt_client import get_mqtt_client
        get_mqtt_client()
