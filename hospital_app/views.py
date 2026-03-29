# hospital_app/views.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from hospital_app.models import Patient, Bed
from sensor_app.mqtt_client import publish_message
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
)
from sensor_app.models import PatientDeviceBedAssignment, Device
from sensor_app.serializers import PatientDeviceBedAssignmentSerializer

import json

User = get_user_model()


@api_view(['GET'])
def get_patient_detail(request, patient_id):
    try:
        patient = Patient.objects.prefetch_related(
            'assignments__device__fluid_bags',
            'assignments__bed__ward__floor',
            'assignments__user',
        ).get(id=patient_id)

        serializer = PatientWithHistorySerializer(patient, context={'request': request})
        return Response(serializer.data)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def create_patient(request):
    serializer = CreatePatientSerializer(data=request.data)

    if serializer.is_valid():
        try:
            patient = serializer.save()
            response_data = {
                "message": "✅ Patient added successfully.",
                "patient": PatientSerializer(patient).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Failed to save patient. Reason: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response(
        {"message": "Validation error.", "errors": serializer.errors},
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['PUT'])
def discharge_patient(request, patient_id):
    """Discharge a patient"""
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = DischargePatientSerializer(patient, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save(discharged_at=request.data.get('discharged_at'))
        return Response(PatientSerializer(patient).data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_patient(request, patient_id):
    """Delete a patient"""
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])  # or ['PATCH'] if you prefer partial updates
def update_patient(request, patient_id):
    """Update an existing patient's details"""
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PatientSerializer(patient, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        detail_serializer = PatientWithHistorySerializer(patient, context={'request': request})
        return Response(detail_serializer.data)
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


@api_view(['GET', 'PUT', 'PATCH'])
def patient_detail_view(request, patient_id):
    """
    Get or Update an existing patient's details.
    """
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'GET':
        serializer = PatientWithHistorySerializer(patient, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            detail_serializer = PatientWithHistorySerializer(patient, context={'request': request})
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def assign_patient_to_bed(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
        bed_id = request.data.get('bed_id')

        if not bed_id:
            return Response({"error": "bed_id is required"}, status=400)

        new_bed = Bed.objects.get(id=bed_id)

        current_assignment = PatientDeviceBedAssignment.objects.filter(
            patient=patient,
            end_time__isnull=True
        ).first()

        device_to_move = current_assignment.device if current_assignment else None

        if current_assignment:
            old_bed = current_assignment.bed
            old_bed.is_occupied = False
            old_bed.save()

            current_assignment.end_time = timezone.now()
            current_assignment.save()

        new_bed.is_occupied = True
        new_bed.save()

        new_assignment = PatientDeviceBedAssignment.objects.create(
            patient=patient,
            bed=new_bed,
            device=device_to_move,    # ✔ move device with patient if exists
            user=request.user
        )

        serializer = PatientSerializer(patient)
        return Response(serializer.data, status=200)

    except Patient.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)

    except Bed.DoesNotExist:
        return Response({"error": "Bed not found"}, status=404)

    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_all_patients(request):
    patients = Patient.objects.all().prefetch_related(
        'assignments__bed__ward__floor'
    )

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

    serializer = PatientListWithLocationSerializer(patients, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def get_patient_bed_history(request, patient_id):
    try:
        assignments = PatientDeviceBedAssignment.objects.filter(patient_id=patient_id).select_related('bed', 'ward', 'floor', 'device').order_by('-start_time')
        data = PatientDeviceBedAssignmentSerializer(assignments, many=True, context={'request': request}).data
        return Response(data)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_device_bed_history(request, patient_id):
    """Get device assignment history for beds where the patient was assigned."""
    try:
        # beds where this patient was assigned (historical + current)
        patient_bed_ids = PatientDeviceBedAssignment.objects.filter(patient_id=patient_id).values_list('bed_id', flat=True).distinct()
        device_assignments = PatientDeviceBedAssignment.objects.filter(bed_id__in=patient_bed_ids, device__isnull=False).select_related('device', 'bed', 'user').order_by('-start_time')
        data = PatientDeviceBedAssignmentSerializer(device_assignments, many=True, context={'request': request}).data
        return Response(data)
    except Patient.DoesNotExist:
        return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_all_patients_with_history(request):
    patients = Patient.objects.prefetch_related(
        'assignments__bed__ward__floor',
        'assignments__device__fluid_bags',
    ).all()
    serializer = PatientWithHistorySerializer(patients, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def get_patient_related_device_history(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    patient_bed_ids = PatientDeviceBedAssignment.objects.filter(patient_id=patient_id).values_list('bed_id', flat=True).distinct()
    device_assignments = PatientDeviceBedAssignment.objects.filter(bed_id__in=patient_bed_ids, device__isnull=False).select_related('device', 'user', 'bed').order_by('-start_time')
    serializer = PatientDeviceBedAssignmentSerializer(device_assignments, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def get_device_bed_history_by_device_id(request, device_id):
    try:
        device = Device.objects.get(id=device_id)
    except Device.DoesNotExist:
        return Response({'error': 'Device not found'}, status=status.HTTP_404_NOT_FOUND)

    device_assignments = PatientDeviceBedAssignment.objects.filter(device_id=device_id).select_related('device', 'user', 'bed').order_by('-start_time')
    serializer = PatientDeviceBedAssignmentSerializer(device_assignments, many=True, context={'request': request})
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
