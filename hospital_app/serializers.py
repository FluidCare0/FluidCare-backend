# hospital_app/serializers.py
from rest_framework import serializers
from .models import Floor, Ward, Bed, Patient
from sensor_app.models import Device, PatientDeviceBedAssignment, FluidBag
from sensor_app.serializers import FluidBagSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

# ========== BASIC STRUCTURE SERIALIZERS ==========

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
        fields = ['floor_number', 'description', 'name']

class WardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ['floor', 'ward_number', 'name', 'description']

class BedCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = ['ward', 'bed_number', 'is_occupied']

# ========== USER & PATIENT SERIALIZERS ==========

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']

class PatientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at']

# ========== DEVICE SERIALIZER ==========

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'mac_address', 'type', 'status']

# ========== UPDATED: PATIENT WITH DEVICE + BED HISTORY ==========

class PatientWithHistorySerializer(serializers.ModelSerializer):
    """Shows a patient's device/bed assignment history with ward & floor context."""
    assignments = serializers.SerializerMethodField()
    current_floor = serializers.SerializerMethodField()
    current_ward = serializers.SerializerMethodField()
    current_bed = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'gender', 'contact',
            'admitted_at', 'discharged_at',
            'assignments', 'current_floor', 'current_ward', 'current_bed'
        ]

    def get_assignments(self, obj):
        assignments = (
            PatientDeviceBedAssignment.objects
            .filter(patient=obj)
            .select_related('device', 'bed', 'ward', 'floor')
        )

        results = []
        for a in assignments:
            results.append({
                'device_id': str(a.device.id) if a.device else None,
                'device_mac': a.device.mac_address if a.device and a.device.mac_address else "N/A",
                'bed_number': a.bed.bed_number if a.bed else None,
                'ward': a.ward.name if a.ward else None,
                'floor': a.floor.name if a.floor else None,
                'start_time': a.start_time,
                'end_time': a.end_time,
            })
        return results

    def get_current_floor(self, obj):
        active = PatientDeviceBedAssignment.objects.filter(patient=obj, end_time__isnull=True).select_related('floor').first()
        return active.floor.name if active and active.floor else None

    def get_current_ward(self, obj):
        active = PatientDeviceBedAssignment.objects.filter(patient=obj, end_time__isnull=True).select_related('ward').first()
        return active.ward.name if active and active.ward else None

    def get_current_bed(self, obj):
        active = PatientDeviceBedAssignment.objects.filter(patient=obj, end_time__isnull=True).select_related('bed').first()
        return active.bed.bed_number if active and active.bed else None


# ========== PATIENT LIST WITH LOCATION (For Quick Overviews) ==========

class PatientListWithLocationSerializer(serializers.ModelSerializer):
    floor = serializers.SerializerMethodField()
    ward = serializers.SerializerMethodField()
    bed = serializers.SerializerMethodField()
    active_devices = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'age', 'gender', 'contact',
            'admitted_at', 'discharged_at',
            'floor', 'ward', 'bed', 'active_devices'
        ]

    def get_floor(self, obj):
        active = (
            PatientDeviceBedAssignment.objects
            .filter(patient=obj, end_time__isnull=True)
            .select_related('floor')
            .first()
        )
        return active.floor.name if active and active.floor else None

    def get_ward(self, obj):
        active = (
            PatientDeviceBedAssignment.objects
            .filter(patient=obj, end_time__isnull=True)
            .select_related('ward')
            .first()
        )
        return active.ward.name if active and active.ward else None

    def get_bed(self, obj):
        active = (
            PatientDeviceBedAssignment.objects
            .filter(patient=obj, end_time__isnull=True)
            .select_related('bed')
            .first()
        )
        return active.bed.bed_number if active and active.bed else None

    def get_active_devices(self, obj):
        active_assignments = (
            PatientDeviceBedAssignment.objects
            .filter(patient=obj, end_time__isnull=True)
            .select_related('device')
        )

        # Use safe null checks and UUID-based identifier
        devices = []
        for a in active_assignments:
            if a.device:  # ✅ Only process if device exists
                devices.append({
                    'device_id': str(a.device.id),
                    'device_mac': a.device.mac_address or "N/A",
                    'type': a.device.type or "Unknown",
                    'status': a.device.status,
                })
        return devices


# ========== CREATE / DISCHARGE PATIENT SERIALIZERS ==========

class CreatePatientSerializer(serializers.ModelSerializer):
    """Serializer for creating a new patient."""

    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'contact', 'admitted_at']

    def validate_contact(self, value):
        if value and Patient.objects.filter(contact=value, is_active=True).exists():
            raise serializers.ValidationError("A patient with this contact already exists.")
        return value

    def create(self, validated_data):
        from django.utils import timezone
        if not validated_data.get('admitted_at'):
            validated_data['admitted_at'] = timezone.now()
        validated_data['is_active'] = True  # Always mark as active when admitted
        return Patient.objects.create(**validated_data)
    
class DischargePatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['discharged_at']
