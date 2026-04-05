from django.db import models


class Notification(models.Model):
    SOURCE_TYPES = [
        ('system', 'System'),
        ('admin', 'Admin'),
    ]
    DELIVERY_SCOPES = [
        ('global', 'Global'),
        ('all_users', 'All Users'),
        ('role', 'Specific Role'),
        ('user', 'Specific User'),
    ]
    NOTIFICATION_TYPES = [
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('error', 'Error'),
    ]
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('med', 'Medium'),
        ('high', 'High'),
    ]

    id = models.AutoField(primary_key=True)
    recipient = models.ForeignKey(
        'auth_app.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_notifications',
    )
    created_by = models.ForeignKey(
        'auth_app.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_notifications',
    )
    device = models.ForeignKey(
        'sensor_app.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    source = models.CharField(max_length=20, choices=SOURCE_TYPES, default='system')
    delivery_scope = models.CharField(max_length=20, choices=DELIVERY_SCOPES, default='global')
    target_role = models.CharField(max_length=20, null=True, blank=True)
    patient_name = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='low')
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    retry_count = models.IntegerField(default=0)
    last_retry = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sensor_app_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='sensor_app__created_5706e6_idx'),
            models.Index(fields=['is_read'], name='sensor_app__is_read_99bcb6_idx'),
            models.Index(fields=['recipient']),
            models.Index(fields=['source', 'delivery_scope']),
        ]

    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
