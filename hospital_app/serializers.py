# hospital_app/serializers.py
from rest_framework import serializers
from .models import Floor, Ward, Bed, Patient
from survey_app.models import DeviceBedAssignmentHistory, PatientBedAssignmentHistory
from survey_app.serializers import PatientBedAssignmentHistorySerializer, DeviceBedAssignmentHistorySerializer # type: ignore # Ensure import is here
from sensor_app.models import Device
from django.contrib.auth import get_user_model

User = get_user_model()



class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ['id', 'ward', 'bed_number', 'is_occupied']

class WardSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)
    
    class Meta:
        model = Ward
        fields = ['id', 'floor', 'ward_number', 'name', 'description', 'beds']

class FloorSerializer(serializers.ModelSerializer):
    wards = WardSerializer(many=True, read_only=True)
    
    class Meta:
        model = Floor
        fields = ['id', 'floor_number', 'name', 'description', 'wards']

class FloorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ['floor_number', 'description']

class WardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['floor', 'ward_number', 'name', 'description']

class BedCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ['ward', 'bed_number', 'is_occupied']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email'] # Removed first_name, last_name as they don't exist on your custom User model

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']

class PatientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'mac_address', 'type', 'status']


class PatientWithHistorySerializer(serializers.ModelSerializer):
    patient_bed_assignments = serializers.SerializerMethodField()
    device_bed_assignments = serializers.SerializerMethodField()

    current_floor = serializers.SerializerMethodField()
    current_ward = serializers.SerializerMethodField()
    current_bed = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'gender', 'contact', 
            'admitted_at', 'discharged_at', 'patient_bed_assignments', 
            'device_bed_assignments',
            'current_floor', 'current_ward', 'current_bed'
        ]

    def get_patient_bed_assignments(self, obj):
        assignments = obj.patient_bed_assignments.all().order_by('-start_time')
        # Use the imported serializer
        return PatientBedAssignmentHistorySerializer(assignments, many=True, context=self.context).data

    def get_device_bed_assignments(self, obj):
        patient_bed_ids = obj.patient_bed_assignments.values_list('bed__id', flat=True).distinct()
        device_assignments = DeviceBedAssignmentHistory.objects.filter(
            bed_id__in=patient_bed_ids
        ).order_by('-start_time')
        # Use the imported serializer
        return DeviceBedAssignmentHistorySerializer(device_assignments, many=True, context=self.context).data

    def get_current_floor(self, obj):
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.ward.floor.floor_number
        return None

    def get_current_ward(self, obj):
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.ward.ward_number
        return None

    def get_current_bed(self, obj):
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.bed_number
        return None

class PatientListWithLocationSerializer(serializers.ModelSerializer):
    floor = serializers.SerializerMethodField()
    ward = serializers.SerializerMethodField()
    bed = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at',
            'floor', 'ward', 'bed'
        ]

    def get_floor(self, obj):
        """Get the floor number from the active bed assignment."""
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.ward.floor.floor_number
        return None

    def get_ward(self, obj):
        """Get the ward number from the active bed assignment."""
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.ward.ward_number
        return None

    def get_bed(self, obj):
        """Get the bed number from the active bed assignment."""
        active_assignment = obj.patient_bed_assignments.filter(end_time__isnull=True).first()
        if active_assignment:
            return active_assignment.bed.bed_number
        return None
    

class CreatePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'contact', 'admitted_at']

class DischargePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['discharged_at']
