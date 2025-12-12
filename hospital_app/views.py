from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from hospital_app.models import Patient, Bed
from sensor_app.mqtt_client import publish_message
from survey_app.models import PatientBedAssignmentHistory, DeviceBedAssignmentHistory
from .models import Floor, Ward
from .serializers import (
    FloorSerializer,
    PatientListWithLocationSerializer,
    WardSerializer,
    BedSerializer,
    FloorCreateSerializer,
    WardCreateSerializer,
    BedCreateSerializer,
    PatientSerializer,
    PatientDetailSerializer,
    PatientWithHistorySerializer,
    CreatePatientSerializer,
    DischargePatientSerializer,
    PatientBedAssignmentHistorySerializer,
    DeviceBedAssignmentHistorySerializer
)

import json


User = get_user_model()


@api_view(['GET'])
def get_patient_detail(request, patient_id):
    try:
        # Prefetch only the patient bed assignments and their related floor/ward/bed structure
        patient = Patient.objects.select_related().prefetch_related(
            'patient_bed_assignments__bed__ward__floor',
            'patient_bed_assignments__patient',
            'patient_bed_assignments__user',
            # Removed device assignment prefetch as it's handled by the serializer method
        ).get(id=patient_id)

        serializer = PatientWithHistorySerializer(patient)
        return Response(serializer.data)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
@api_view(['POST'])
def create_patient(request):
    """Create a new patient"""
    serializer = CreatePatientSerializer(data=request.data)
    if serializer.is_valid():
        patient = serializer.save()
        return Response(PatientSerializer(patient).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
def discharge_patient(request, patient_id):
    """Discharge a patient"""
    try:
        patient = Patient.objects.get(id=patient_id)
        serializer = DischargePatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            # Update discharge time
            serializer.save(discharged_at=request.data.get('discharged_at'))
            return Response(PatientSerializer(patient).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_patient(request, patient_id):
    """Delete a patient"""
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['PUT']) # or ['PATCH'] if you prefer partial updates
def update_patient(request, patient_id):
    """Update an existing patient's details"""
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PatientSerializer(patient, data=request.data, partial=True) # Use partial=True for PATCH
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_hospital_structure(request):
    floors = Floor.objects.all().prefetch_related('wards__beds')
    serializer = FloorSerializer(floors, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def add_floor(request):
    serializer = FloorCreateSerializer(data=request.data)
    if serializer.is_valid():
        floor = serializer.save()
        return Response(FloorSerializer(floor).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_ward(request):
    serializer = WardCreateSerializer(data=request.data)
    if serializer.is_valid():
        ward = serializer.save()
        return Response(WardSerializer(ward).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_bed(request):
    serializer = BedCreateSerializer(data=request.data)
    if serializer.is_valid():
        bed = serializer.save()
        return Response(BedSerializer(bed).data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_floor(request, floor_id):
    try:
        floor = Floor.objects.get(id=floor_id)
        floor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Floor.DoesNotExist:
        return Response({'error': 'Floor not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_ward(request, ward_id):
    try:
        ward = Ward.objects.get(id=ward_id)
        ward.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Ward.DoesNotExist:
        return Response({'error': 'Ward not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
def delete_bed(request, bed_id):
    try:
        bed = Bed.objects.get(id=bed_id)
        bed.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Bed.DoesNotExist:
        return Response({'error': 'Bed not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET', 'PUT']) 
def patient_detail_view(request, patient_id):
    """
    Get or Update an existing patient's details.
    """
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'GET':
        # Use the detailed serializer for GET
        serializer = PatientWithHistorySerializer(patient)
        return Response(serializer.data)

    elif request.method == 'PUT': # or 'PATCH'
        # Use the PatientSerializer for updates
        serializer = PatientSerializer(patient, data=request.data, partial=True) # Use partial=True for PATCH
        if serializer.is_valid():
            serializer.save()
            # Return the updated patient data using the detail serializer
            detail_serializer = PatientWithHistorySerializer(patient)
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def assign_patient_to_bed(request, patient_id):
   
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)

    bed_id = request.data.get('bed_id')
    if not bed_id:
        return Response({'error': 'Bed ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        new_bed = Bed.objects.get(id=bed_id)
    except Bed.DoesNotExist:
        return Response({'error': 'Bed not found'}, status=status.HTTP_404_NOT_FOUND)

    active_assignment = PatientBedAssignmentHistory.objects.filter(
        patient=patient,
        end_time__isnull=True
    ).first()

    if new_bed.is_occupied and (not active_assignment or active_assignment.bed.id != new_bed.id):
        return Response({'error': 'Bed is already occupied'}, status=status.HTTP_400_BAD_REQUEST)

    # If there is an active assignment, end it and mark the old bed as unoccupied
    if active_assignment:
        active_assignment.end_time = timezone.now()
        active_assignment.save()
        # Mark the old bed as unoccupied
        old_bed = active_assignment.bed
        old_bed.is_occupied = False
        old_bed.save()

    # Create a new assignment
    new_assignment = PatientBedAssignmentHistory.objects.create(
        patient=patient,
        user=user,
        bed=new_bed
    )
    # Mark the new bed as occupied
    new_bed.is_occupied = True
    new_bed.save()

    # Fetch the updated patient details to return
    updated_patient = Patient.objects.select_related().prefetch_related(
        'patient_bed_assignments__bed__ward__floor',
        'patient_bed_assignments__patient',
        'patient_bed_assignments__user',
    ).get(id=patient_id)
    serializer = PatientWithHistorySerializer(updated_patient)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_all_patients(request):
    """Get all patients with optional filters and current location."""
    # Prefetch related bed assignment data to calculate current location
    patients = Patient.objects.all().prefetch_related(
        'patient_bed_assignments__bed__ward__floor'
    )
    
    # Apply filters
    search = request.GET.get('search', '')
    if search:
        patients = patients.filter(
            Q(name__icontains=search) |
            Q(contact__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        patients = patients.filter(discharged_at__isnull=True)
    elif status_filter == 'discharged':
        patients = patients.filter(discharged_at__isnull=False)

    gender_filter = request.GET.get('gender', '')
    if gender_filter:
        patients = patients.filter(gender=gender_filter)

    # Use the new serializer that includes location
    serializer = PatientListWithLocationSerializer(patients, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_patient_bed_history(request, patient_id):
    """Get patient bed assignment history"""
    try:
        assignments = PatientBedAssignmentHistory.objects.filter(patient_id=patient_id)
        serializer = PatientBedAssignmentHistorySerializer(assignments, many=True)
        return Response(serializer.data)
    except:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_device_bed_history(request, patient_id):
    """Get device bed assignment history for patient's beds"""
    try:
        # Get all beds where this patient was assigned
        patient_assignments = PatientBedAssignmentHistory.objects.filter(
            patient_id=patient_id
        ).values_list('bed_id', flat=True)
        
        # Get all device assignments for those beds
        device_assignments = DeviceBedAssignmentHistory.objects.filter(
            bed_id__in=patient_assignments
        )
        
        serializer = DeviceBedAssignmentHistorySerializer(device_assignments, many=True)
        return Response(serializer.data)
    except:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_all_patients_with_history(request):
    patients = Patient.objects.select_related().prefetch_related(
        'patient_bed_assignments__bed__ward__floor',
        'patient_bed_assignments__patient',
        'patient_bed_assignments__user',
        # Removed device assignment prefetch as it's handled by the serializer method
    ).all()
    serializer = PatientWithHistorySerializer(patients, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_patient_related_device_history(request, patient_id):
    
    # Validate patient exists
    patient = get_object_or_404(Patient, id=patient_id)

    # Get all beds where this patient was assigned (including past assignments)
    patient_bed_ids = PatientBedAssignmentHistory.objects.filter(
        patient_id=patient_id
    ).values_list('bed_id', flat=True).distinct()

    # Get all device assignments for those specific beds
    device_assignments = DeviceBedAssignmentHistory.objects.filter(
        bed_id__in=patient_bed_ids
    ).select_related('device', 'user', 'bed').order_by('-start_time') # Order by start_time descending

    # Serialize the data
    serializer = DeviceBedAssignmentHistorySerializer(device_assignments, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET'])
def get_device_bed_history_by_device_id(request, device_id):
    from sensor_app.models import Device
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    device_assignments = DeviceBedAssignmentHistory.objects.filter(
        device_id=device_id # Assuming 'device_id' is the foreign key field in DeviceBedAssignmentHistory
    ).select_related('device', 'user', 'bed').order_by('-start_time') # Order by start_time descending

    serializer = DeviceBedAssignmentHistorySerializer(device_assignments, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['PUT'])
def update_bed_status(request, bed_id):
    try:
        bed = Bed.objects.get(id=bed_id)
        bed.is_occupied = not bed.is_occupied
        bed.save()
        return Response(BedSerializer(bed).data)
    except Bed.DoesNotExist:
        return Response({'error': 'Bed not found'}, status=status.HTTP_404_NOT_FOUND)






