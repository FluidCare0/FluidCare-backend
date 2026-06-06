import json
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db.models import Prefetch
from sensor_app.models import Device, FluidBag, PatientDeviceBedAssignment, SensorReading
from django.shortcuts import get_object_or_404, render
from sensor_app.mqtt_client import publish_message
from sensor_app.serializers import (
    DeviceSerializer,
    DeviceWithCurrentAssignmentSerializer,
    FluidBagSerializer,
    PatientDeviceBedAssignmentSerializer,
    SensorReadingSerializer,
)
from hospital_app.models import Patient, Bed, Ward
from hospital_app.serializers import PatientSerializer

logger = logging.getLogger('django')

# Protocol codes
RES_NODE_ASSIGN = 201


def sensor_dashboard(request):
    return render(request, 'sensor_monitor.html')


@api_view(['GET'])
def get_all_devices(request):
    active_assignments = (
        PatientDeviceBedAssignment.objects
        .filter(end_time__isnull=True, device__isnull=False)
        .select_related('patient', 'device', 'bed', 'ward', 'floor')
    )
    assigned_device_ids = {a.device_id for a in active_assignments}

    # Devices that exist but have no active assignment (exclude completed)
    standalone_devices = (
        Device.objects
        .filter(type='node')
        .exclude(status='completed')
        .exclude(id__in=assigned_device_ids)
        .prefetch_related('fluid_bags')
    )

    data = list(PatientDeviceBedAssignmentSerializer(active_assignments, many=True).data)

    for device in standalone_devices:
        data.append({
            "id": None,
            "device": DeviceSerializer(device).data,
            "patient_name": None,
            "user_name": None,
            "bed_number": None,
            "ward_name": None,
            "ward_number": None,
            "floor_number": None,
            "start_time": None,
            "end_time": None,
            "notes": None,
        })

    return Response(data)


@api_view(['GET'])
def get_patient_details_by_device(request, device_id):
    assignment = PatientDeviceBedAssignment.objects.filter(
        device_id=device_id,
        end_time__isnull=True
    ).select_related('patient').first()

    if not assignment:
        return Response({'detail': 'No active assignment found for this device.'}, status=404)

    serializer = PatientSerializer(assignment.patient)
    return Response(serializer.data)


@api_view(['GET'])
def get_patient_assignment_history_by_device(request, device_id):
    history = PatientDeviceBedAssignment.objects.filter(device_id=device_id)\
        .select_related('patient', 'device', 'bed', 'ward', 'floor')\
        .order_by('-start_time')

    serializer = PatientDeviceBedAssignmentSerializer(history, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def get_device_assignment_history(request, device_id):
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
def get_sensor_history_view(request, device_id):
    hours = int(request.GET.get('hours', 24))
    time_threshold = timezone.now() - timedelta(hours=hours)

    try:
        device = get_object_or_404(Device, id=device_id)
    except Device.DoesNotExist:
        pass

    readings = SensorReading.objects.filter(
        fluid_bag__device=device,
        timestamp__gte=time_threshold
    ).values('reading', 'timestamp').order_by('timestamp')

    return Response(list(readings))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sensor_history(request, device_id):
    hours = int(request.GET.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)

    device = get_object_or_404(Device, id=device_id)
    fluid_bag = device.fluid_bags.first()

    if not fluid_bag:
        return Response({'error': 'No fluid bag linked to this device.'}, status=404)

    readings = SensorReading.objects.filter(fluid_bag=fluid_bag, timestamp__gte=start_time)\
        .order_by('timestamp')

    serializer = SensorReadingSerializer(readings, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def register_node(request):
    """
    Assign device to patient. Creates device on-the-fly if not already present.
    1. Get or create Device for MAC (unassigned)
    2. Create FluidBag + Assignment
    3. Send code 201 → Master → Node (node stores the ID)
    4. Node replies code 202 → handle_node_confirm → status = online
    """
    mac = request.data.get('mac')
    patient_id = request.data.get('patient_id')
    bed_id = request.data.get('bed_id')
    fluid_type = request.data.get('fluid_type')
    fluid_capacity = request.data.get('fluid_capacity')

    if not all([mac, patient_id, bed_id, fluid_type, fluid_capacity]):
        missing = [
            k for k, v in {
                'mac': mac, 'patient_id': patient_id,
                'bed_id': bed_id, 'fluid_type': fluid_type,
                'fluid_capacity': fluid_capacity
            }.items() if not v
        ]
        return Response(
            {"error": f"Missing required fields: {', '.join(missing)}."},
            status=400
        )

    # Get existing unassigned device or create one — device creation happens at assignment time
    device = Device.objects.filter(mac_address=mac, status='unassigned').first()
    if not device:
        # Check if already actively assigned
        active = Device.objects.filter(mac_address=mac).exclude(status='completed').first()
        if active:
            return Response(
                {"error": f"Device with MAC {mac} is already active (status={active.status})."},
                status=400
            )
        device = Device.objects.create(mac_address=mac, type='node', status='unassigned')

    patient = get_object_or_404(Patient, id=patient_id)
    bed = get_object_or_404(Bed, id=bed_id)
    ward = bed.ward
    floor = ward.floor

    # --- Close any old active assignments for this patient ---
    old_assignments = PatientDeviceBedAssignment.objects.filter(
        patient=patient,
        end_time__isnull=True
    ).exclude(bed=bed)

    for old_ass in old_assignments:
        old_ass.end_time = timezone.now()
        old_ass.save()
        if old_ass.bed:
            old_ass.bed.is_occupied = False
            old_ass.bed.save()

    # --- Create assignment ---
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

    # --- Create fluid bag ---
    fluid_bag = FluidBag.objects.create(
        device=device,
        type=fluid_type,
        capacity_ml=fluid_capacity
    )

    assignment.device = device
    assignment.save()

    # --- Send code 201 → Master → Node ---
    topic = getattr(settings, 'MQTT_TOPIC_MASTER_IN', 'be_project/master/in')
    payload = {
        "request_code": RES_NODE_ASSIGN,
        "mac": device.mac_address,
        "node_id": str(device.id)
    }

    logger.info(f"📤 Sending code 201 to master for MAC {mac}, node_id {device.id}")
    publish_message(topic, payload)

    return Response({
        "message": "Device assignment created. Node ID sent to device.",
        "node_id": str(device.id),
        "patient": patient.name,
        "bed": bed.bed_number if hasattr(bed, 'bed_number') else str(bed.id),
        "ward": ward.name,
        "floor": getattr(floor, 'name', f"Floor {getattr(floor, 'floor_number', '')}")
    }, status=200)