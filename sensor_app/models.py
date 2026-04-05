from django.utils import timezone
from django.db import models
import uuid
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

from hospital_app.models import Bed, Floor, Patient, User, Ward

class Device(models.Model):
    TYPE = [
        ('node', 'Node'),
        ('repeater', 'Repeater'),
        ('master', 'Master')
    ]
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('completed', 'Task Completed'),
    ]
    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, primary_key=True)  # Changed to editable=False
    mac_address = models.CharField(max_length=150, db_index=True)
    type = models.CharField(max_length=50, choices=TYPE, default='node')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    installed_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now) # ✅ add this
    updated_at = models.DateTimeField(auto_now=True)

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


    def __str__(self):
        return f'{self.get_type_display()} on {self.device.mac_address}'
    
    class Meta:
        indexes = [
            models.Index(fields=['device']),
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
    
class PatientDeviceBedAssignment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True)
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name="assignments", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    def clean(self):
        """Ensure each patient, device, and bed have only one active assignment."""

        # validate device only if present
        if self.device:
            if PatientDeviceBedAssignment.objects.filter(device=self.device, end_time__isnull=True).exclude(pk=self.pk).exists():
                raise ValidationError(f"Device {self.device.id} already in use.")

        # validate bed always
        if self.bed:
            if PatientDeviceBedAssignment.objects.filter(bed=self.bed, end_time__isnull=True).exclude(pk=self.pk).exists():
                raise ValidationError(f"Bed {self.bed.bed_number} already occupied.")

    def save(self, *args, **kwargs):
        """Auto-fill ward and floor if not set."""
        if self.bed and not self.ward:
            self.ward = self.bed.ward
        if self.ward and not self.floor:
            self.floor = self.ward.floor
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        patient_name = self.patient.name if self.patient else "Unassigned Patient"
        device_mac = self.device.mac_address if self.device else "No Device"
        bed_number = self.bed.bed_number if self.bed else "No Bed"
        return f"{patient_name} ↔ {device_mac} ↔ Bed {bed_number}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device"], condition=Q(end_time__isnull=True), name="unique_active_device_assignment"),
            models.UniqueConstraint(fields=["bed"], condition=Q(end_time__isnull=True), name="unique_active_bed_assignment"),
            models.UniqueConstraint(fields=["bed", "device"], condition=Q(end_time__isnull=True), name="unique_active_bed_device_assignment")
        ]
        indexes = [
            models.Index(fields=["ward"]),
            models.Index(fields=["floor"]),
        ]
