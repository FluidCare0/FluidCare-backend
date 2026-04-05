from rest_framework import serializers

from notification_app.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()
    patient_name = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    recipient_name = serializers.SerializerMethodField()
    recipient_role = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    delivery_scope = serializers.CharField(read_only=True)
    target_role = serializers.CharField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'title',
            'message',
            'patient_name',
            'source',
            'recipient_name',
            'recipient_role',
            'created_by_name',
            'delivery_scope',
            'target_role',
            'notification_type',
            'severity',
            'is_read',
            'is_resolved',
            'retry_count',
            'last_retry',
            'created_at',
            'time',
        ]

    def get_time(self, obj):
        return obj.created_at.isoformat()

    def get_recipient_name(self, obj):
        return obj.recipient.name if obj.recipient else None

    def get_recipient_role(self, obj):
        return obj.recipient.role if obj.recipient else None

    def get_created_by_name(self, obj):
        return obj.created_by.name if obj.created_by else None
