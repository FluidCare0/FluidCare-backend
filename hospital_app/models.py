import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q, UniqueConstraint
from django.core.exceptions import ValidationError

# from sensor_app.models import Device

User = get_user_model()

class Patient(models.Model):
    GENDER = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    name = models.CharField(max_length=200, null=True, blank=True)
    age = models.PositiveBigIntegerField(null=True)
    gender = models.CharField(max_length=20, choices=GENDER)
    contact = models.CharField(max_length=15, null=True, blank=True)  # Changed to CharField
    email = models.EmailField(null=True, blank=True)
    admitted_at = models.DateTimeField(null=True)
    discharged_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)  # New field

    def get_current_bed_assignment(self):
        """Return the currently active bed assignment"""
        return self.patient_bed_assignments.filter(end_time__isnull=True).first()

    def get_current_device_assignment(self):
        """Return the currently active device assignment"""
        return self.device_assignments.filter(end_time__isnull=True).first()

    @property
    def current_floor(self):
        assignment = self.get_current_bed_assignment()
        return assignment.bed.ward.floor.floor_number if assignment else None

    @property
    def current_ward(self):
        assignment = self.get_current_bed_assignment()
        return assignment.bed.ward.ward_number if assignment else None

    @property
    def current_bed(self):
        assignment = self.get_current_bed_assignment()
        return assignment.bed.bed_number if assignment else None
    
    @property
    def current_device(self):
        assignment = self.get_current_device_assignment()
        return assignment.device if assignment else None
    
    def __str__(self):
        return f'{self.name} - {self.id}'

    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'admitted_at']),
            models.Index(fields=['contact']),
        ]

class Floor(models.Model):
    floor_number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Floor {self.floor_number} - {self.name or ""}'
    
    class Meta:
        ordering = ['floor_number']
   
class Ward(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='wards', null=True, blank=True)
    ward_number = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Ward {self.ward_number} ({self.name}) - Floor {self.floor.floor_number}'

    class Meta:
        unique_together = ['floor', 'ward_number']
        ordering = ['floor', 'ward_number']
        indexes = [
            models.Index(fields=['floor', 'is_active']),
        ]

class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds', null=True, blank=True)
    bed_number = models.PositiveIntegerField()
    is_occupied = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'Bed {self.bed_number} - {self.ward.name} (Ward {self.ward.ward_number})'

    class Meta:
        unique_together = ['ward', 'bed_number']
        ordering = ['ward', 'bed_number']
        indexes = [
            models.Index(fields=['ward', 'is_occupied', 'is_active']),
        ]

