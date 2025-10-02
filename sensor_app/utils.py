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

def determine_status(load, fluid_bag):
    if load <= fluid_bag.threshold_low:
        return 'LOW'
    elif load >= fluid_bag.threshold_high:
        return 'HIGH'
    else:
        return 'NORMAL'
    


def process_mqtt_message(mqtt_data):
    try:
        node_id = mqtt_data.get('node_id')
        node_mac = mqtt_data.get('node_mac')
        reading = mqtt_data.get('reading')
        battery_percent = mqtt_data.get('battery_percent')
        timestamp_unix = mqtt_data.get('timestamp')
        via = bool(mqtt_data.get('via'))
        repeater_mac = mqtt_data.get('repeater_mac')
        master_mac = mqtt_data.get('master_mac')

        timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)
        device = get_device(str(node_id))
        fluid_bag = get_fluid_bag(device)

        if not fluid_bag:
            print(f'No fluid bag found for device {node_id}')
            return None
        
        status = determine_status(reading, fluid_bag)
        
        if status in ['LOW', 'HIGH']:
            from sensor_app.tasks import send_alert_notification
            send_alert_notification.delay(node_id)


        # sensor_reading = SensorReading.objects.create(
        #     FluidBag = fluid_bag,
        #     fluid_level = reading,
        #     timestamp = timestamp,
        #     status = status,
        #     via = via,
        #     master_mac = str(master_mac) if master_mac else None
        # )
        
        # device.status = True
        # device.last_seen = timestamp
        # device.save()

        # return sensor_reading
    
    except Device.DoesNotExist:
        print(f'Device with MAC address {node_id} nor found ')
        return None
    except Exception as e:
        print(f'Error processing MQTT message: {e}')
        return None
    
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

