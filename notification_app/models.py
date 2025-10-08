# from django.db import models

# class Alert(models.Model):
#     PRIORITY_LEVELS = [
#         ('INFO', 'Information'),
#         ('WARNING', 'Warning'),
#         ('CRITICAL', 'Critical'),
#         ('EMERGENCY', 'Emergency'),
#     ]
    
#     STATUS_CHOICES = [
#         ('ACTIVE', 'Active'),
#         ('ACKNOWLEDGED', 'Acknowledged'),
#         ('RESOLVED', 'Resolved'),
#     ]
    
#     sensor_reading = models.ForeignKey('sensor_app.SensorReading', on_delete=models.CASCADE)
#     priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS)
#     message = models.TextField()
#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
#     created_at = models.DateTimeField(auto_now_add=True)
#     acknowledged_at = models.DateTimeField(null=True, blank=True)
#     acknowledged_by = models.ForeignKey('auth_app.User', on_delete=models.SET_NULL, null=True, blank=True)
#     resolved_at = models.DateTimeField(null=True, blank=True)
    
#     class Meta:
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['status', '-created_at']),
#             models.Index(fields=['priority', 'status']),
#         ]
    
#     def __str__(self):
#         return f"{self.priority} Alert - {self.message[:50]}"
