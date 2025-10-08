import logging
from django.utils import timezone
from datetime import datetime, timezone as date_timezone
from sensor_app.models import Device, FluidBag, SensorReading
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.cache import cache

CACHE_TIMEOUT = 60 * 10 

mqtt_logger = logging.getLogger('mqtt')
django_logger = logging.getLogger('django')


    
def get_bed_info(device):
        from survey_app.models import DeviceBedAssignmentHistory
        
        try:
            assignment = DeviceBedAssignmentHistory.objects.filter(
                device=device,
                end_time__isnull=True
            ).select_related('bed__ward__floor').first()
            
            if assignment:
                return {
                    'bed_number': assignment.bed.bed_number,
                    'ward_number': assignment.bed.ward.ward_number,
                    'ward_name': assignment.bed.ward.name,
                    'floor_number': assignment.bed.ward.floor.floor_number,
                }
        except Exception as e:
            django_logger.error(f"Error getting bed info: {e}")
        
        return None

def generate_device_id(data):
    pass