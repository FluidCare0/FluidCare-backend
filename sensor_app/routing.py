from django.urls import re_path
from sensor_app import consumers

websocket_urlpatterns = [
    re_path(r'ws/sensors/$', consumers.SensorConsumer.as_asgi()),
]