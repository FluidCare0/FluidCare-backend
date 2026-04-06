# sensor_app/serializers.py
from rest_framework import serializers
from .models import Device, FluidBag, PatientDeviceBedAssignment, SensorReading
from hospital_app.models import Patient, Bed, Ward
from django.contrib.auth import get_user_model

User = get_user_model()


class WardSerializerForDevice(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['id', 'ward_number', 'name']


class BedSerializerForDevice(serializers.ModelSerializer):
    ward = WardSerializerForDevice(read_only=True)

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
        fields = "__all__"


class DeviceSerializer(serializers.ModelSerializer):
    fluid_bags = FluidBagSerializer(many=True, read_only=True)

    class Meta:
        model = Device
        fields = ['id', 'mac_address', 'type', 'status', 'fluid_bags']


class DeviceWithCurrentAssignmentSerializer(serializers.ModelSerializer):
    fluidBag = FluidBagSerializer(read_only=True)
    current_patient = serializers.SerializerMethodField()
    current_bed_number = serializers.SerializerMethodField()
    current_ward_number = serializers.SerializerMethodField()
    current_ward_name = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'mac_address', 'type', 'status',
            'fluidBag',
            'current_patient', 'current_bed_number', 'current_ward_number', 'current_ward_name'
        ]

    def get_current_patient(self, obj):
        # Fixed: use correct property name 'current_bed_assignment'
        assignment = obj.current_bed_assignment
        if assignment and assignment.patient:
            return assignment.patient.name
        return None


class SensorReadingSerializer(serializers.ModelSerializer):
    level = serializers.IntegerField(source='reading')

    class Meta:
        model = SensorReading
        fields = ['level', 'smoothed_weight', 'timestamp', 'battery_percent']


class PatientDeviceBedAssignmentSerializer(serializers.ModelSerializer):
    device = DeviceSerializer(read_only=True)
    # Fixed: Added default=None to all FK dot-notation sources to prevent 
    # AttributeError crashes if ward/floor/patient is None
    patient_name = serializers.CharField(source='patient.name', default=None, read_only=True)
    user_name = serializers.CharField(source='user.name', default=None, read_only=True)
    bed_number = serializers.IntegerField(source='bed.bed_number', default=None, read_only=True)
    ward_name = serializers.CharField(source='ward.name', default=None, read_only=True)
    ward_number = serializers.IntegerField(source='ward.ward_number', default=None, read_only=True)
    floor_number = serializers.IntegerField(source='floor.floor_number', default=None, read_only=True)

    class Meta:
        model = PatientDeviceBedAssignment
        fields = [
            'id', 'patient_name', 'user_name', 'device', 'bed_number',
            'ward_name', 'ward_number', 'floor_number',
            'start_time', 'end_time', 'notes'
        ]