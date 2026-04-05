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

    # Create ONE shared notification row (recipient=None) per send action.
    # delivery_scope + target_role already capture the intended audience.
    # The get_notifications view returns rows where recipient=current_user OR recipient=None,
    # so all targeted users see this single row — no N-duplicate rows in the sidebar.
    notification = Notification.objects.create(
        recipient=None,               # shared broadcast, not per-user
        created_by=sender,
        source='admin',
        delivery_scope=delivery_scope,
        target_role=target_role,
        title=title,
        message=message,
        notification_type=notification_type,
        severity=severity,
    )

    # One WebSocket broadcast → one toast → one sidebar entry
    send_notification_to_websocket(notification)

    # Return a list for API compatibility (count field in the response)
    return [notification]
