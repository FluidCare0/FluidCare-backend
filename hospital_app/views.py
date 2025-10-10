from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from hospital_app.models import Patient
from survey_app.models import PatientBedAssignmentHistory, DeviceBedAssignmentHistory
from .models import Floor, Ward, Bed
from .serializers import (
    FloorSerializer, WardSerializer, BedSerializer,
    FloorCreateSerializer, WardCreateSerializer, BedCreateSerializer,
    PatientSerializer, PatientDetailSerializer, PatientWithHistorySerializer,
    CreatePatientSerializer, DischargePatientSerializer,
    PatientBedAssignmentHistorySerializer, DeviceBedAssignmentHistorySerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

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

@api_view(['PUT'])
def update_bed_status(request, bed_id):
    try:
        bed = Bed.objects.get(id=bed_id)
        bed.is_occupied = not bed.is_occupied
        bed.save()
        return Response(BedSerializer(bed).data)
    except Bed.DoesNotExist:
        return Response({'error': 'Bed not found'}, status=status.HTTP_404_NOT_FOUND)
    

@api_view(['GET'])
def get_all_patients(request):
    """Get all patients with optional filters"""
    patients = Patient.objects.all()
    
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
    
    serializer = PatientSerializer(patients, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_patient_detail(request, patient_id):
    """Get patient with assignment history"""
    try:
        patient = Patient.objects.get(id=patient_id)
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
    """Get all patients with their assignment history"""
    patients = Patient.objects.all()
    serializer = PatientWithHistorySerializer(patients, many=True)
    return Response(serializer.data)