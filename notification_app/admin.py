from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from notification_app.forms import AdminNotificationForm
from notification_app.models import Notification
from notification_app.services import create_admin_notifications, resolve_notification_recipients

User = get_user_model()


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    change_list_template = 'admin/notification_app/notification/change_list.html'
    list_display = (
        'title',
        'recipient',
        'created_by',
        'source',
        'delivery_scope',
        'target_role',
        'notification_type',
        'severity',
        'is_read',
        'is_resolved',
        'created_at',
    )
    list_filter = ('source', 'delivery_scope', 'target_role', 'notification_type', 'severity', 'is_read', 'is_resolved', 'created_at')
    search_fields = ('title', 'message', 'device__mac_address', 'patient_name', 'recipient__name', 'recipient__mobile', 'created_by__name')
    readonly_fields = ('created_at',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'send/',
                self.admin_site.admin_view(self.send_notification_view),
                name='notification_app_notification_send',
            ),
        ]
        return custom_urls + urls

    def send_notification_view(self, request):
        form = AdminNotificationForm(request.POST or None)

        if request.method == 'POST' and form.is_valid():
            recipients, delivery_scope, target_role = resolve_notification_recipients(
                request.user,
                form.cleaned_data['target_mode'],
                form.cleaned_data.get('target_role'),
                getattr(form.cleaned_data.get('target_user'), 'id', None),
            )

            if not recipients:
                form.add_error(None, 'No active users match the selected target.')
            else:
                notifications = create_admin_notifications(
                    sender=request.user,
                    recipients=recipients,
                    delivery_scope=delivery_scope,
                    target_role=target_role,
                    title=form.cleaned_data['title'],
                    message=form.cleaned_data['message'],
                    notification_type=form.cleaned_data['notification_type'],
                    severity=form.cleaned_data['severity'],
                )

                count = len(notifications)
                self.message_user(
                    request,
                    f"Sent {count} custom notification{'s' if count != 1 else ''}.",
                    level=messages.SUCCESS,
                )
                return HttpResponseRedirect(reverse('admin:notification_app_notification_changelist'))

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Send Custom Notification',
            'form': form,
        }
        return TemplateResponse(request, 'admin/notification_app/send_notification.html', context)
