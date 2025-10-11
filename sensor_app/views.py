# sensor_app/views.py - OPTIMIZED VERSION
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db.models import Prefetch
from sensor_app.models import Device, FluidBag, SensorReading
from django.shortcuts import render
from sensor_app.serializers import DeviceWithCurrentAssignmentSerializer, FluidBagSerializer
from hospital_app.models import Patient, Bed, Ward
from survey_app.models import DeviceBedAssignmentHistory, PatientBedAssignmentHistory

class SensorReadingViewSet(viewsets.ReadOnlyModelViewSet):
    pass

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
    ).values('reading', 'timestamp').order_by('timestamp')
    
    return Response(list(readings))

class registerDevice(APIView):
    authentication_classes = [authentication.TokenAuthentication]
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        pass

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_devices(request):
    """
    Get all devices of type 'node' with their current patient assignment and fluid bag details.
    OPTIMIZED: Uses prefetch_related with Prefetch objects to minimize database queries.
    """
    
    # Get all active patient assignments upfront to reduce queries
    active_patient_assignments = PatientBedAssignmentHistory.objects.filter(
        end_time__isnull=True
    ).select_related('patient', 'bed')
    
    # Create a dictionary mapping bed_id to patient for quick lookups
    bed_to_patient = {
        assignment.bed_id: assignment.patient 
        for assignment in active_patient_assignments
    }
    
    # Query DeviceBedAssignmentHistory for active assignments with optimized prefetching
    active_device_assignments = DeviceBedAssignmentHistory.objects.filter(
        end_time__isnull=True,
        device__type='node'
    ).select_related(
        'device',           # Join assignment -> device
        'bed',              # Join assignment -> bed
        'bed__ward',        # Join bed -> ward
        'user'              # Join assignment -> user
    ).prefetch_related(
        'device__fluidBag'  # Prefetch FluidBags for all devices
    ).all()

    # Prepare the list of data structures
    device_data_list = []
    
    for device_assignment in active_device_assignments:
        device = device_assignment.device
        bed = device_assignment.bed
        ward = bed.ward if bed else None
        
        # Get patient from the pre-built dictionary (no extra query!)
        patient = bed_to_patient.get(bed.id) if bed else None

        # Get the FluidBag for this device
        fluid_bags = device.fluidBag.all()
        fluid_bag_instance = fluid_bags.first() if fluid_bags.exists() else None
        fluid_bag_data = FluidBagSerializer(fluid_bag_instance).data if fluid_bag_instance else None

        # Build the data dictionary
        device_data = {
            'id': str(device.id),
            'mac_address': device.mac_address,
            'type': device.type,
            'status': device.status,
            'fluidBag': fluid_bag_data,
            'current_patient': patient.name if patient else None,
            'current_bed_number': bed.bed_number if bed else None,
            'current_ward_number': ward.ward_number if ward else None,
            'current_ward_name': ward.name if ward else None,
        }
        device_data_list.append(device_data)

    return Response(device_data_list)