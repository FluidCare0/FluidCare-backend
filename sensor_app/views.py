# sensor_app/views.py - OPTIMIZED VERSION
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
from sensor_app.models import Device, FluidBag, SensorReading
from django.shortcuts import get_object_or_404, render
from sensor_app.serializers import DeviceWithCurrentAssignmentSerializer, FluidBagSerializer, SensorReadingSerializer
from hospital_app.models import Patient, Bed, Ward
from survey_app.models import DeviceBedAssignmentHistory, PatientBedAssignmentHistory
# Import serializers from their respective apps
from survey_app.serializers import PatientBedAssignmentHistorySerializer, DeviceBedAssignmentHistorySerializer
from hospital_app.serializers import PatientSerializer # Import from hospital_app

logger = logging.getLogger('django')

class SensorReadingViewSet(viewsets.ReadOnlyModelViewSet):
    pass

def sensor_dashboard(request):
    return render(request, 'sensor_monitor.html')

@api_view(['POST']) # Or PUT/PATCH if you prefer
# @permission_classes([IsAuthenticated])
def remove_device_from_dashboard(request, device_id):
    """
    API endpoint to manually remove a device from the dashboard view.
    Sends an MQTT command to the device to stop, and sets Device.removed_from_dashboard to True.
    """
    device = get_object_or_404(Device, id=device_id)
    pass

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_all_devices(request):
    """
    Get all devices of type 'node' with their current patient assignment and fluid bag details.
    OPTIMIZED: Uses prefetch_related with Prefetch objects to minimize database queries.
    NOW: Filters out devices marked as removed_from_dashboard.
    """
    
    # Get all active patient assignments upfront to reduce queries
    active_patient_assignments = PatientBedAssignmentHistory.objects.filter(
        end_time__isnull=True
    ).select_related('patient', 'bed')
    
    # Create a dictionary mapping bed_id to patient for quick lookups
    bed_to_patient = {
        assignment.bed_id: assignment.patient  # type: ignore
        for assignment in active_patient_assignments
    }
    
    # Query DeviceBedAssignmentHistory for active assignments with optimized prefetching
    # --- ADD FILTER FOR removed_from_dashboard (assuming you added the field) ---
    active_device_assignments = DeviceBedAssignmentHistory.objects.filter(
        end_time__isnull=True,
        device__type='node',
        device__removed_from_dashboard=False # Filter out manually removed devices
    ).select_related(
        'device',           # Join assignment -> device
        'bed',              # Join assignment -> bed
        'bed__ward',        # Join bed -> ward
        'user'              # Join assignment -> user
    ).prefetch_related(
        'device__fluidBag'  # Prefetch FluidBags for all devices
    ).all()
    # ---

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

        # Determine status based on backend status and stop_at field
        status_display = 'Offline' # Default to Offline
        if device.status and not device.stop_at:
            # DB status is True and stop_at is not set -> Active
            status_display = 'Activate'
        elif device.stop_at:
            # stop_at is set -> Task Completed or Disconnected (determine based on context or separate field if needed)
            # For simplicity, let's call it 'Inactive' here, but you might want to differentiate
            status_display = 'Task_Completed' # Or 'Disconnected' if process_disconnect sets it

        # Build the data dictionary
        device_data = {
            'id': str(device.id),
            'mac_address': device.mac_address,
            'type': device.type,
            'status': device.status, # Boolean status from DB
            'status_display': status_display, # String for frontend display
            'stop_at': device.stop_at,
            # 'removed_from_dashboard': device.removed_from_dashboard, # Usually not needed if filtered out
            'fluidBag': fluid_bag_data,
            'current_patient': patient.name if patient else None,
            'current_bed_number': bed.bed_number if bed else None,
            'current_ward_number': ward.ward_number if ward else None,
            'current_ward_name': ward.name if ward else None,
        }
        device_data_list.append(device_data)

    return Response(device_data_list)


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_patient_details_by_device(request, device_id):
    """
    Get detailed patient information for the patient currently assigned to the given device.
    Handles potential serialization errors gracefully.
    """
    device = get_object_or_404(Device, id=device_id)
    device_assignment = device.current_assignment # This is a DeviceBedAssignmentHistory object

    if device_assignment and device_assignment.bed: # Check if the device is assigned to a bed
        bed = device_assignment.bed
        # Now, find the *current* patient assigned to *this* bed
        # Use the related name 'patient_bed_assignments' from the Patient model
        # or the PatientBedAssignmentHistory model directly
        patient_assignment = PatientBedAssignmentHistory.objects.filter(
            bed=bed,
            end_time__isnull=True # Find the active assignment
        ).select_related('patient').first() # Get the first (and should be only) active assignment

        if patient_assignment and patient_assignment.patient:
            patient = patient_assignment.patient
            try:
                # Use the PatientSerializer from hospital_app.serializers
                serializer = PatientSerializer(patient)
                patient_data = serializer.data

                # Optional: Add a check if the serialized data seems valid
                # (e.g., contains expected keys like 'name').
                if 'name' in patient_data:
                    return Response(patient_data)
                else:
                    logger.warning(f"PatientSerializer returned incomplete data for patient {patient.id} via device {device_id}")
                    return Response({
                        'id': str(patient.id),
                        'name': patient.name,
                        'age': patient.age,
                        'gender': patient.gender,
                        'contact': patient.contact,
                        'admitted_at': patient.admitted_at,
                        'discharged_at': patient.discharged_at
                    })

            except Exception as e:
                # If serialization fails (e.g., due to missing prefetched related objects),
                # log the error and return a minimal response based on the assignment.
                logger.error(f"Error serializing patient {patient.id} details for device {device_id}: {e}", exc_info=True)
                return Response({
                    'id': str(patient.id),
                    'name': patient.name,
                    'age': patient.age,
                    'gender': patient.gender,
                    'contact': patient.contact,
                    'admitted_at': patient.admitted_at,
                    'discharged_at': patient.discharged_at
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # No patient is currently assigned to the bed where the device is located
            return Response({'detail': 'No patient currently assigned to the bed where this device is located.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # The device itself is not assigned to any bed
        return Response({'detail': 'Device is not currently assigned to any bed.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_patient_assignment_history_by_device(request, device_id):
    """
    Get the patient bed assignment history for the patient currently assigned to the given device.
    """
    device = get_object_or_404(Device, id=device_id)
    device_assignment = device.current_assignment # This is a DeviceBedAssignmentHistory object

    if device_assignment and device_assignment.bed: # Check if the device is assigned to a bed
        bed = device_assignment.bed
        # Find the *current* patient assigned to *this* bed
        patient_assignment = PatientBedAssignmentHistory.objects.filter(
            bed=bed,
            end_time__isnull=True
        ).select_related('patient').first()

        if patient_assignment and patient_assignment.patient:
            patient = patient_assignment.patient
            # Get all history entries for this patient
            history = PatientBedAssignmentHistory.objects.filter(patient=patient).select_related('patient', 'user', 'bed').order_by('-start_time')
            # Use the PatientBedAssignmentHistorySerializer from survey_app.serializers
            serializer = PatientBedAssignmentHistorySerializer(history, many=True, context={'request': request})
            return Response(serializer.data)
        else:
            # No patient currently assigned to the bed
            return Response([])
    else:
        # Device not assigned to a bed
        return Response([])


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def get_device_assignment_history(request, device_id):
    """
    Get the device bed assignment history for the given device ID.
    """
    device = get_object_or_404(Device, id=device_id)
    # Get all history entries for this device
    history = DeviceBedAssignmentHistory.objects.filter(device=device).select_related('device', 'user', 'bed').order_by('-start_time')
    # Use the DeviceBedAssignmentHistorySerializer from survey_app.serializers
    serializer = DeviceBedAssignmentHistorySerializer(history, many=True, context={'request': request})
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
    hours = int(request.GET.get('hours', 24))
    try:
        device = Device.objects.get(id=device_id)
        fluid_bag = device.fluidBag.first()
        if not fluid_bag:
            return Response({'error': 'No fluid bag'}, status=404)
        start_time = timezone.now() - timedelta(hours=hours)
        readings = SensorReading.objects.filter(fluidBag=fluid_bag, timestamp__gte=start_time).order_by('timestamp')
        return Response(SensorReadingSerializer(readings, many=True).data)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=404)