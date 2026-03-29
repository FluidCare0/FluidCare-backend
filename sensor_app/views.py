# sensor_app/views.py - OPTIMIZED VERSION
import json
import logging
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
from sensor_app.models import Device, FluidBag, PatientDeviceBedAssignment, SensorReading
from django.shortcuts import get_object_or_404, render
from sensor_app.mqtt_client import publish_message
from sensor_app.serializers import DeviceWithCurrentAssignmentSerializer, FluidBagSerializer, PatientDeviceBedAssignmentSerializer, SensorReadingSerializer
from hospital_app.models import Patient, Bed, Ward
from hospital_app.serializers import PatientSerializer 

logger = logging.getLogger('django')



def sensor_dashboard(request):
    return render(request, 'sensor_monitor.html')

@api_view(['GET'])
def get_all_devices(request):    
    active_assignments = (
        PatientDeviceBedAssignment.objects
        .filter(end_time__isnull=True, device__isnull=False)   # 👈 exclude device NULL
        .select_related('patient', 'device', 'bed', 'ward', 'floor')
    )
    
    serializer = PatientDeviceBedAssignmentSerializer(active_assignments, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_patient_details_by_device(request, device_id):
    """
    Get patient details for the active assignment of the given device.
    """
    assignment = PatientDeviceBedAssignment.objects.filter(
        device_id=device_id,
        end_time__isnull=True
    ).select_related('patient').first()

    if not assignment:
        return Response({'detail': 'No active assignment found for this device.'}, status=404)

    serializer = PatientSerializer(assignment.patient)
    return Response(serializer.data)

@api_view(['POST'])
def remove_device_from_dashboard(request, device_id):
    """
    Manually deactivate a device and mark its assignment as ended.
    """
    device = get_object_or_404(Device, id=device_id)
    assignment = PatientDeviceBedAssignment.objects.filter(device=device, end_time__isnull=True).first()

    if not assignment:
        return Response({'error': 'No active assignment found for this device.'}, status=404)

    assignment.end_time = timezone.now()
    assignment.save()

    # Send MQTT command to stop
    topic = 'be_project/device/stop'
    payload = {"command": "STOP", "node_id": str(device.id)}
    publish_message(topic, payload)

    device.status = False
    device.save(update_fields=['status'])

    return Response({'message': 'Device removed successfully and stop command sent.'})


@api_view(['GET'])
def get_patient_assignment_history_by_device(request, device_id):
    """
    Get all assignment records (active + historical) for a given device.
    """
    history = PatientDeviceBedAssignment.objects.filter(device_id=device_id)\
        .select_related('patient', 'device', 'bed', 'ward', 'floor')\
        .order_by('-start_time')

    serializer = PatientDeviceBedAssignmentSerializer(history, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_device_assignment_history(request, device_id):
    """
    Return the assignment history (active + past) for the given device.
    Uses the unified PatientDeviceBedAssignment model.
    """
    device = get_object_or_404(Device, id=device_id)

    history = PatientDeviceBedAssignment.objects.filter(
        device=device
    ).select_related(
        'patient', 'device', 'bed', 'ward', 'floor', 'user'
    ).order_by('-start_time')

    serializer = PatientDeviceBedAssignmentSerializer(history, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sensor_history_view(request, device_id): # device_id is now the UUID
    """
    Get sensor reading history for a device identified by its UUID.
    """
    hours = int(request.GET.get('hours', 24))
    time_threshold = timezone.now() - timedelta(hours=hours)

    try:
        # Find the device by its UUID (primary key)
        # get_object_or_404 will automatically return 404 if not found
        device = get_object_or_404(Device, id=device_id) # Use id instead of mac_address
    except Device.DoesNotExist:
        # This case is handled by get_object_or_404, which raises Http404
        # If you want custom error handling, you can remove get_object_or_404
        # and handle the exception manually, but the default behavior is fine.
        pass # get_object_or_404 handles this

    # Find sensor readings associated with the device's fluid bags
    # This assumes SensorReading links to FluidBag, which links to Device
    readings = SensorReading.objects.filter(
        fluidBag__device=device, # Filter by the device linked via FluidBag
        timestamp__gte=time_threshold
    ).values('reading', 'timestamp').order_by('timestamp') # Select only needed fields

    return Response(list(readings))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sensor_history(request, device_id):
    """
    Get sensor reading history for a given device (last N hours).
    """
    hours = int(request.GET.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)

    device = get_object_or_404(Device, id=device_id)
    fluid_bag = device.fluid_bags.first()

    if not fluid_bag:
        return Response({'error': 'No fluid bag linked to this device.'}, status=404)

    readings = SensorReading.objects.filter(fluidBag=fluid_bag, timestamp__gte=start_time)\
        .order_by('timestamp')

    serializer = SensorReadingSerializer(readings, many=True)
    return Response(serializer.data)
    

@api_view(['POST'])
def register_node(request):
    mac = request.data.get('mac')
    patient_id = request.data.get('patient_id')
    bed_number = request.data.get('bed')
    fluid_type = request.data.get('fluid_type')
    fluid_capacity = request.data.get('fluid_capacity')

    if not all([mac, patient_id, bed_number, fluid_type, fluid_capacity]):
        return Response({"error": "Missing required fields."}, status=400)

    patient = get_object_or_404(Patient, id=patient_id)
    bed = get_object_or_404(Bed, bed_number=bed_number)
    ward = bed.ward
    floor = ward.floor

    assignment, created = PatientDeviceBedAssignment.objects.get_or_create(
        patient=patient,
        bed=bed,
        end_time__isnull=True,
        defaults={
            "ward": ward,
            "floor": floor,
            "user": request.user if request.user.is_authenticated else None
        }
    )

    bed.is_occupied = True
    bed.save()

    device = Device.objects.create(
        mac_address=mac,
        type='node'
    )

    fluid_bag = FluidBag.objects.create(
        device=device,
        type=fluid_type,
        capacity_ml=fluid_capacity
    )

    assignment.device = device
    assignment.save()

    topic = 'be_project/test/in'
    payload = {
        "request_code": 202,
        "mac": device.mac_address,
        "node_id": str(device.id)
    }

    logger.info(f"📤 MQTT Payload Sent: {json.dumps(payload)}")
    publish_message(topic, payload)

    return Response({
        "message": "Device registered and assigned successfully.",
        "node_id": str(device.id),
        "patient": patient.name,
        "bed": bed.bed_number if hasattr(bed, 'bed_number') else str(bed.id),
        "ward": ward.name,
        "floor": getattr(floor, 'name', f"Floor {getattr(floor, 'floor_number', '')}")
    }, status=200)
