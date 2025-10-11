# sensor_app/serializers.py
from rest_framework import serializers
from .models import Device, FluidBag
from hospital_app.models import Patient, Bed, Ward # Import related models
from django.contrib.auth import get_user_model

User = get_user_model()

# Optional: Reuse existing serializers if they exist and are compatible
# from hospital_app.serializers import PatientSerializer, BedSerializer, WardSerializer # If available
# from survey_app.serializers import DeviceBedAssignmentHistorySerializer # If available

# If not reusing, create minimal serializers for related fields needed for display
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

# Serializer for Device including FluidBag and Current Assignment details
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
