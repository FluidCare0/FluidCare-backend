from django.core.management.base import BaseCommand
from sensor_app.mqtt_client import get_mqtt_client
import time

class Command(BaseCommand):
    help = 'Start MQTT client to listen for sensor data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting MQTT client...'))
        
        mqtt_client = get_mqtt_client()
        
        self.stdout.write(self.style.SUCCESS('MQTT client started successfully!'))
        self.stdout.write('Press Ctrl+C to stop...')
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping MQTT client...'))
            mqtt_client.disconnect()
            self.stdout.write(self.style.SUCCESS('MQTT client stopped'))
