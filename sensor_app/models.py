from django.db import models
import uuid

class Device(models.Model):
    TYPE = [
        ('node', 'node'),
        ('repeater', 'repeater'),
        ('master', 'master')
    ]
    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, primary_key=True) 
    mac_address = models.CharField(max_length=150, unique=True)
    type = models.CharField(max_length=50, choices=TYPE, default='node')
    status = models.BooleanField(default=False)  # Active / Inactive
    installed_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.type.capitalize()} - {self.mac_address}'

    @property
    def current_assignment(self):
        return self.assignments.filter(end_time__isnull=True).first() # type: ignore

    @property
    def current_bed(self):
        assignment = self.current_assignment
        return assignment.bed if assignment else None

    @property
    def current_ward(self):
        bed = self.current_bed
        return bed.ward if bed else None

    @property
    def current_floor(self):
        ward = self.current_ward
        return ward.floor if ward else None

    @property
    def assigned_by_user(self):
        assignment = self.current_assignment
        return assignment.user if assignment else None
    
class FluidBag(models.Model):
    TYPE = [
        ('iv_bag', 'IV Bag'),
        ('blood_bag', 'Blood Bag'),
        ('urine_bag', 'Urine Bag'),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='fluidBag')
    type = models.CharField(max_length=50, choices=TYPE, null=True, blank=True)
    capacity_ml = models.PositiveBigIntegerField()
    threshold_low = models.PositiveIntegerField(blank=True, null=True)
    threshold_high = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f'{self.type} on {self.device}'
    
class SensorReading(models.Model):
    fluidBag = models.ForeignKey(FluidBag, on_delete=models.CASCADE)
    reading = models.PositiveIntegerField(editable=False)
    timestamp = models.DateTimeField(blank=True, null=True, editable=False)
    via = models.BooleanField(default=False)
    battery_percent = models.FloatField(null=True, blank=True)
    repeater_mac = models.CharField(max_length=150, null=True, blank=True)
    master_mac = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['fluidBag', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.fluidBag} - {self.reading}ml at {self.timestamp}'



# be_project/node_53b987544add496e80208d6b1606a75e

# {
#   "node_id": "53b987544add496e80208d6b1606a75e",
#   "node_mac": "AA:BB:CC:DD:EE:01",
#   "reading": 66.76,
#   "battery_percent": 65.07,
#   "timestamp": 1859550537,
#   "date": "2025-10-04",
#   "time": "15:44:12",
#   "via": 0,
#   "repeater_mac": null,
#   "master_mac": "11:22:33:44:55:01"
# }
