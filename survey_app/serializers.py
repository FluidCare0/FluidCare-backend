from rest_framework import serializers
from hospital_app.models import Patient, Bed, Ward, Floor
from sensor_app.models import Device
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']

class PatientSerializer(serializers.ModelSerializer):
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
        fields = ['id', 'mac_address', 'type', 'status']

