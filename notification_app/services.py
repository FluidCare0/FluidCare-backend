from django.contrib.auth import get_user_model

from notification_app.models import Notification

User = get_user_model()


def resolve_notification_recipients(sender, target_mode, target_role=None, target_user_id=None):
    users = User.objects.filter(is_active=True)

    if target_mode == 'all_users':
        return list(users.exclude(id=sender.id)), 'all_users', None

    if target_mode == 'all_users_include_me':
        return list(users), 'all_users', None

    if target_mode == 'role':
        return list(users.filter(role=target_role)), 'role', target_role

    if target_mode == 'user' and target_user_id:
        target_user = users.filter(id=target_user_id).first()
        if target_user:
            return [target_user], 'user', target_user.role

    return [], 'user', None


def create_admin_notifications(*, sender, recipients, delivery_scope, target_role, title, message, notification_type, severity):
    from notification_app.tasks import send_notification_to_websocket

    # One row per recipient so each user owns their copy — read/resolve state is isolated.
    notifications = []
    for recipient in recipients:
        notification = Notification.objects.create(
            recipient=recipient,
            created_by=sender,
            source='admin',
            delivery_scope=delivery_scope,
            target_role=target_role,
            title=title,
            message=message,
            notification_type=notification_type,
            severity=severity,
        )
        notifications.append(notification)
        send_notification_to_websocket(notification)

    return notifications
