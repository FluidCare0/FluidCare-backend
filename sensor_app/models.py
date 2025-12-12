from django.db import models
import uuid
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

from hospital_app.models import Patient, User

class Device(models.Model):
    TYPE = [
        ('node', 'Node'),
        ('repeater', 'Repeater'),
        ('master', 'Master')
    ]
    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, primary_key=True)  # Changed to editable=False
    mac_address = models.CharField(max_length=150, db_index=True)
    type = models.CharField(max_length=50, choices=TYPE, default='node')
    status = models.BooleanField(default=False)  # Active / Inactive
    installed_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    stop_at = models.DateTimeField(null=True, blank=True)
    removed_from_dashboard = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.type.capitalize()} - {self.mac_address}'

    @property
    def current_bed_assignment(self):
        """Get current bed assignment (if any)"""
        return self.bed_assignments.filter(end_time__isnull=True).first() # type: ignore

    @property
    def current_patient_assignment(self):
        """Get current patient assignment"""
        return self.patient_assignments.filter(end_time__isnull=True).first()

    @property
    def current_bed(self):
        assignment = self.current_bed_assignment
        return assignment.bed if assignment else None

    @property
    def current_patient(self):
        assignment = self.current_patient_assignment
        return assignment.patient if assignment else None

    @property
    def current_ward(self):
        bed = self.current_bed
        return bed.ward if bed else None

    @property
    def current_floor(self):
        ward = self.current_ward
        return ward.floor if ward else None

    class Meta:
        indexes = [
            models.Index(fields=['type', 'status']),
            models.Index(fields=['status', 'removed_from_dashboard']),
        ]
   
class FluidBag(models.Model):
    TYPE = [
        ('iv_bag', 'IV Bag'),
        ('blood_bag', 'Blood Bag'),
        ('urine_bag', 'Urine Bag'),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='fluid_bags', null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE)
    capacity_ml = models.PositiveBigIntegerField()
    threshold_low = models.PositiveIntegerField(blank=True, null=True)
    threshold_high = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.get_type_display()} on {self.device.mac_address}'
    
    class Meta:
        indexes = [
            models.Index(fields=['device', 'is_active']),
        ]
   
class SensorReading(models.Model):
    fluid_bag = models.ForeignKey(FluidBag, on_delete=models.CASCADE, related_name='readings', null=True, blank=True)
    reading = models.PositiveIntegerField(editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    via = models.BooleanField(default=False)
    battery_percent = models.FloatField(null=True, blank=True)
    repeater_mac = models.CharField(max_length=150, null=True, blank=True)
    master_mac = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['fluid_bag', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.fluid_bag.get_type_display()} - {self.reading}ml at {self.timestamp}'
    
class DevicePatientAssignment(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='patient_assignments', null=True, blank=True)
    fluid = models.ForeignKey(FluidBag, on_delete=models.CASCADE, related_name='patient_assignments', null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='device_assignments', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_patient_assignments', null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def clean(self):
        # Check if device is already assigned to another patient
        active_device_assignment = DevicePatientAssignment.objects.filter(
            device=self.device,
            end_time__isnull=True
        ).exclude(pk=self.pk).exists()

        if active_device_assignment:
            raise ValidationError(
                f"Device {self.device.mac_address} is already assigned to another patient."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.device.mac_address} monitoring {self.patient.name} (Started: {self.start_time})'

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['device'],
                condition=Q(end_time__isnull=True),
                name='unique_active_device_patient_assignment'
            )
        ]
        indexes = [
            models.Index(fields=['device', 'end_time']),
            models.Index(fields=['patient', 'end_time']),
            models.Index(fields=['-start_time']),
        ]
        verbose_name = 'Device-Patient Assignment'
        verbose_name_plural = 'Device-Patient Assignments'