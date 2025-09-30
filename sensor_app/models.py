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
    last_seen = models.DateTimeField(null=True, blank=True)
    floor = models.ForeignKey('hospital_app.Floor', on_delete=models.SET_NULL, null = True, blank = True)

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
    STATUS_CHOICES = [
        ('LOW', 'Low'),
        ('NORMAL', 'Normal'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    ]
    fluidBag = models.ForeignKey(FluidBag, on_delete=models.CASCADE)
    fluid_level = models.PositiveIntegerField(editable=False)
    timestamp = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=100, null=True, blank=True) # not decided yet to keep or not 
    via = models.BooleanField(default=False)
    # repeater_mac = models.CharField(max_length=150, null=True, blank=True)
    master_mac = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['fluidBag', '-timestamp']),
        ]
    
    def __str__(self):
        return f'{self.fluidBag} - {self.fluid_level}ml at {self.timestamp}'

    
# {
#   "node_id": 7,
#   "floor": 3, (in question to add not added in utlis.py file of sensor_app)
#   "load": 3728,
#   "timestamp": 1759150249,
#   "via": 1,
#   "repeater_mac": 170, (no need of repeater mac because thier will be multiple repeator)
#   "master_mac": 187
# }