# sensor_app/serializers.py
from rest_framework import serializers
from .models import Device, FluidBag, PatientDeviceBedAssignment, SensorReading
from hospital_app.models import Patient, Bed, Ward # Import related models
from django.contrib.auth import get_user_model

User = get_user_model()

class WardSerializerForDevice(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['id', 'ward_number', 'name']

class BedSerializerForDevice(serializers.ModelSerializer):
    ward = WardSerializerForDevice(read_only=True) # Include ward details

    class Meta:
        model = Bed
        fields = ['id', 'bed_number', 'ward']

class PatientSerializerForDevice(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name']

class FluidBagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FluidBag
        fields = ['id', 'type', 'capacity_ml', 'threshold_low', 'threshold_high']

class DeviceWithCurrentAssignmentSerializer(serializers.ModelSerializer):
    fluidBag = FluidBagSerializer(read_only=True) # Include fluid bag details
    current_patient = serializers.SerializerMethodField() # Get current patient name
    current_bed_number = serializers.SerializerMethodField() # Get current bed number
    current_ward_number = serializers.SerializerMethodField() # Get current ward number
    current_ward_name = serializers.SerializerMethodField() # Get current ward name (optional)

    class Meta:
        model = Device
        fields = [
            'id', 'mac_address', 'type', 'status', # Device model fields
            'fluidBag', # Related fluid bag details
            'current_patient', 'current_bed_number', 'current_ward_number', 'current_ward_name' # Current assignment details
        ]

    def get_current_patient(self, obj):
        """Get the name of the patient currently assigned to this device."""
        assignment = obj.current_assignment # Use the property from your Device model
        if assignment and assignment.patient:
            return assignment.patient.name
        return None

    def get_current_bed_number(self, obj):
        """Get the bed number where the device is currently assigned."""
        assignment = obj.current_assignment
        if assignment and assignment.bed:
            return assignment.bed.bed_number
        return None

    def get_current_ward_number(self, obj):
        """Get the ward number where the device is currently assigned."""
        assignment = obj.current_assignment
        if assignment and assignment.bed and assignment.bed.ward:
            return assignment.bed.ward.ward_number
        return None

    def get_current_ward_name(self, obj):
        """Get the ward name where the device is currently assigned."""
        assignment = obj.current_assignment
        if assignment and assignment.bed and assignment.bed.ward:
            return assignment.bed.ward.name
        return None

class SensorReadingSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(source='reading')
    class Meta:
        model = SensorReading
        fields = ['level', 'timestamp', 'battery_percent']

class DeviceSerializer(serializers.ModelSerializer):
    fluid_bags = FluidBagSerializer(many=True, read_only=True)
    class Meta:
        model = Device
        fields = ['id', 'mac_address', 'type', 'status', 'stop_at', 'fluid_bags']


class PatientDeviceBedAssignmentSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    bed_number = serializers.IntegerField(source='bed.bed_number', read_only=True)
    ward_name = serializers.CharField(source='ward.name', read_only=True)
    ward_number = serializers.IntegerField(source='ward.ward_number', read_only=True)
    floor_number = serializers.IntegerField(source='floor.floor_number', read_only=True)

    class Meta:
        model = PatientDeviceBedAssignment
        fields = [
            'id', 'patient_name', 'device', 'bed_number',
            'ward_name', 'ward_number', 'floor_number',
            'start_time', 'end_time', 'notes'
        ]