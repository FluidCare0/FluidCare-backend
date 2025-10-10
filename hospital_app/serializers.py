from rest_framework import serializers
from .models import Floor, Ward, Bed, Patient
from survey_app.models import DeviceBedAssignmentHistory, PatientBedAssignmentHistory
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
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']

class PatientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']

class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = ['id', 'floor_number', 'description']

class WardSerializer(serializers.ModelSerializer):
    floor = FloorSerializer(read_only=True)
    
    class Meta:
        model = Ward
        fields = ['id', 'floor', 'ward_number', 'name', 'description']

class BedSerializer(serializers.ModelSerializer):
    ward = WardSerializer(read_only=True)
    
    class Meta:
        model = Bed
        fields = ['id', 'ward', 'bed_number', 'is_occupied']

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'mac_address', 'device_type', 'name', 'is_active']

class PatientBedAssignmentHistorySerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    bed = BedSerializer(read_only=True)
    
    class Meta:
        model = PatientBedAssignmentHistory
        fields = ['id', 'patient', 'user', 'bed', 'start_time', 'end_time']

class DeviceBedAssignmentHistorySerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    bed = BedSerializer(read_only=True)
    
    class Meta:
        model = DeviceBedAssignmentHistory
        fields = ['id', 'device', 'user', 'bed', 'start_time', 'end_time']

class PatientWithHistorySerializer(serializers.ModelSerializer):
    patient_bed_assignments = PatientBedAssignmentHistorySerializer(many=True, read_only=True)
    device_bed_assignments = DeviceBedAssignmentHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'gender', 'contact', 
            'admitted_at', 'discharged_at', 'patient_bed_assignments', 
            'device_bed_assignments'
        ]

class CreatePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'contact', 'admitted_at']

class DischargePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['discharged_at']