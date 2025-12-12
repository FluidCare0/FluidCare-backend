import uuid
from django.db import models
from hospital_app.models import Bed, Patient
from sensor_app.models import Device
from django.contrib.auth import get_user_model
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

User = get_user_model()

class DeviceBedAssignmentHistory(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='assignments', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    def clean(self):
        active_assignment = DeviceBedAssignmentHistory.objects.filter(
            device=self.device,
            end_time__isnull=True
        ).exclude(pk=self.pk).exists()

        if active_assignment:
            raise ValidationError(
                f"Device {self.device.mac_address} is already assigned to another bed and is active."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['device'],
                condition=Q(end_time__isnull=True),
                name='unique_active_device_assignment'
            )
        ]


class PatientBedAssignmentHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_bed_assignments', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)

    def clean(self):
        active_assignment = PatientBedAssignmentHistory.objects.filter(
            patient=self.patient,
            end_time__isnull=True
        ).exclude(pk=self.pk).exists()

        if active_assignment:
            raise ValidationError(
                f"Patient {self.patient} is already assigned to a bed and is active."
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['patient'],
                condition=Q(end_time__isnull=True),
                name='unique_active_patient_bed_assignment'
            )
        ]