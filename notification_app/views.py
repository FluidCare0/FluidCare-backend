from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from notification_app.models import Notification
from notification_app.serializers import NotificationSerializer
from notification_app.services import create_admin_notifications, resolve_notification_recipients


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    notifications = Notification.objects.filter(
        Q(recipient=request.user) | Q(recipient__isnull=True)
    ).filter(
        is_read=False,
        is_resolved=False,
    )[:50]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notification_history(request):
    notifications = Notification.objects.filter(
        Q(recipient=request.user) | Q(recipient__isnull=True)
    ).filter(
        Q(is_read=True) | Q(is_resolved=True)
    )[:100]
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_admin_notification_history(request):
    if request.user.role not in ['root_admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    notifications = Notification.objects.filter(source='admin').select_related('recipient', 'created_by')

    if request.user.role != 'root_admin':
        notifications = notifications.filter(created_by=request.user)

    serializer = NotificationSerializer(notifications[:150], many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(
            Q(id=notification_id),
            Q(recipient=request.user) | Q(recipient__isnull=True),
        )
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'success'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_notification(request, notification_id):
    try:
        notification = Notification.objects.get(
            Q(id=notification_id),
            Q(recipient=request.user) | Q(recipient__isnull=True),
        )
        notification.is_resolved = True
        notification.is_read = True
        notification.save(update_fields=['is_resolved', 'is_read'])
        return Response({'status': 'success'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=404)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    Notification.objects.filter(
        Q(recipient=request.user) | Q(recipient__isnull=True),
        is_read=False,
    ).update(is_read=True)
    return Response({'status': 'success'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_custom_notification(request):
    if request.user.role not in ['root_admin', 'manager']:
        return Response({'error': 'Permission denied'}, status=403)

    title = request.data.get('title', '').strip()
    message = request.data.get('message', '').strip()
    notification_type = request.data.get('notification_type', 'info')
    severity = request.data.get('severity', 'low')
    target_mode = request.data.get('target_mode', 'all_users')
    target_role = request.data.get('target_role')
    target_user_id = request.data.get('target_user_id')

    if not title or not message:
        return Response({'error': 'Title and message are required'}, status=400)

    valid_notification_types = {choice[0] for choice in Notification.NOTIFICATION_TYPES}
    valid_severities = {choice[0] for choice in Notification.SEVERITY_LEVELS}
    valid_target_modes = {'all_users', 'all_users_include_me', 'role', 'user'}

    if notification_type not in valid_notification_types:
        return Response({'error': 'Invalid notification type'}, status=400)

    if severity not in valid_severities:
        return Response({'error': 'Invalid severity'}, status=400)

    if target_mode not in valid_target_modes:
        return Response({'error': 'Invalid target mode'}, status=400)

    recipients, delivery_scope, resolved_target_role = resolve_notification_recipients(
        request.user,
        target_mode,
        target_role,
        target_user_id,
    )

    if not recipients:
        return Response({'error': 'No active users match the selected target'}, status=400)

    created_notifications = create_admin_notifications(
        sender=request.user,
        recipients=recipients,
        delivery_scope=delivery_scope,
        target_role=resolved_target_role,
        title=title,
        message=message,
        notification_type=notification_type,
        severity=severity,
    )

    return Response({
        'status': 'success',
        'count': len(created_notifications),
    })
