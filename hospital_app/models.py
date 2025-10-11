import uuid
from django.db import models
from django.contrib.auth import get_user_model

from sensor_app.models import Device

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
    contact = models.PositiveIntegerField(null=True)
    admitted_at = models.DateTimeField(null=True)
    discharged_at = models.DateTimeField(blank=True, null=True)

    def get_current_bed_assignment(self):
        """Return the currently active bed assignment"""
        return self.patient_bed_assignments.filter(end_time__isnull=True).first() # type: ignore

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
    
    def __str__(self):
        return f'{self.name}- {self.id}'


class Floor(models.Model):
    floor_number = models.PositiveIntegerField(null=True)
    name = models.CharField(max_length=150, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Floor {self.floor_number}'
    
class Ward(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE, related_name='wards')
    ward_number = models.PositiveIntegerField(null=True)
    name = models.TextField(max_length=150)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Ward {self.ward_number} of Floor {self.floor.floor_number}'


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.PositiveIntegerField()
    is_occupied = models.BooleanField(default=False)
    

    def __str__(self):
        return f'Bed {self.bed_number} of Ward {self.ward.ward_number}'

