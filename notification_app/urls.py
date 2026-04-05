from django.urls import path

from notification_app import views

urlpatterns = [
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/history/', views.get_notification_history, name='get_notification_history'),
    path('notifications/admin-history/', views.get_admin_notification_history, name='get_admin_notification_history'),
    path('notifications/send/', views.send_custom_notification, name='send_custom_notification'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/<int:notification_id>/resolve/', views.resolve_notification, name='resolve_notification'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
