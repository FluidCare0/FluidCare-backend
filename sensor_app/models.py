from django.db import models

class Device(models.Model):
    TYPE = [
        ('node', 'node'),
        ('repeater', 'repeater'),
        ('master', 'master')
    ]
    mac_address = models.CharField(max_length=150, unique=True)
    type = models.CharField(max_length=50, choices=TYPE, default='node')
    status = models.BooleanField(default=False)
    installed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.type} ID-{self.mac_address}'
    
class FluidBag(models.Model):
    TYPE = [
        ('iv_bag', 'IV Bag'),
        ('blood_bag', 'Blood Bag'),
        ('urine_bag', 'Urine Bag'),
    ]
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='fluidBag')
    type = models.CharField(max_length=50, choices=TYPE, null=True, blank=True)
    capacity_ml = models.PositiveBigIntegerField()
    threshold_low = models.PositiveIntegerField()
    threshold_high = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.type} on {self.device}'
    

class SensorReading(models.Model):
    fluidBag = models.ForeignKey(FluidBag, on_delete=models.CASCADE)
    fluid_level = models.PositiveIntegerField(editable=False)
    timestamp = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=100, null=True, blank=True) # not decided yet to keep or not 

