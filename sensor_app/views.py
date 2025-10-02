from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.utils import timezone
from datetime import timedelta
from sensor_app.models import Device, FluidBag, SensorReading
from django.shortcuts import render

class SensorReadingViewSet(viewsets.ReadOnlyModelViewSet):
    pass
    # queryset = SensorReading.objects.all().select_related('fluidBag__device')
    
    # @action(detail=False, methods=['get'])
    # def latest(self, request):
    #     latest_readings = []
        
    #     devices = Device.objects.filter(type='node', status=True)
    #     for device in devices:
    #         reading = SensorReading.objects.filter(
    #             fluidBag__device=device
    #         ).order_by('-timestamp').first()
            
    #         if reading:
    #             latest_readings.append({
    #                 'device_id': device.mac_address,
    #                 'fluid_bag_type': reading.fluidBag.type,
    #                 'fluid_level': reading.fluid_level,
    #                 'status': reading.status,
    #                 'timestamp': reading.timestamp,
    #             })
        
    #     return Response(latest_readings)
    
    # @action(detail=False, methods=['get'])
    # def by_floor(self, request):
    #     floor = request.query_params.get('floor')
    #     if not floor:
    #         return Response(
    #             {'error': 'Floor parameter required'}, 
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
        
    #     # Get devices on the floor
    #     from survey_app.models import DeviceBedAssignmentHistory
        
    #     assignments = DeviceBedAssignmentHistory.objects.filter(
    #         bed__ward__floor__floor_number=floor,
    #         end_time__isnull=True
    #     ).select_related('device', 'bed')
        
    #     readings = []
    #     for assignment in assignments:
    #         reading = SensorReading.objects.filter(
    #             fluidBag__device=assignment.device
    #         ).order_by('-timestamp').first()
            
    #         if reading:
    #             readings.append({
    #                 'device_id': assignment.device.mac_address,
    #                 'bed_number': assignment.bed.bed_number,
    #                 'ward_number': assignment.bed.ward.ward_number,
    #                 'fluid_bag_type': reading.fluidBag.type,
    #                 'fluid_level': reading.fluid_level,
    #                 'status': reading.status,
    #                 'timestamp': reading.timestamp,
    #             })
        
    #     return Response(readings)
    
    # @action(detail=False, methods=['get'])
    # def alerts(self, request):
    #     """Get active alerts (low/high status)"""
    #     time_threshold = timezone.now() - timedelta(minutes=5)
        
    #     alerts = SensorReading.objects.filter(
    #         timestamp__gte=time_threshold,
    #         status__in=['LOW', 'HIGH']
    #     ).select_related('fluidBag__device').order_by('-timestamp')
        
    #     alert_data = []
    #     for alert in alerts:
    #         alert_data.append({
    #             'device_id': alert.fluidBag.device.mac_address,
    #             'fluid_bag_type': alert.fluidBag.type,
    #             'fluid_level': alert.fluid_level,
    #             'status': alert.status,
    #             'timestamp': alert.timestamp,
    #         })
        
    #     return Response(alert_data)

def sensor_dashboard(request):
    return render(request, 'sensor_monitor.html')

@api_view(['GET'])
def sensor_history(request, device_id):
    """Get sensor reading history"""
    hours = int(request.GET.get('hours', 24))
    time_threshold = timezone.now() - timedelta(hours=hours)
    
    readings = SensorReading.objects.filter(
        fluidBag__device__mac_address=device_id,
        timestamp__gte=time_threshold
    ).values('fluid_level', 'timestamp', 'status').order_by('timestamp')
    
    return Response(list(readings))