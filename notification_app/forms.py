from django import forms
from django.contrib.auth import get_user_model

from notification_app.models import Notification

User = get_user_model()


class AdminNotificationForm(forms.Form):
    TARGET_MODE_CHOICES = [
        ('all_users', 'All Users'),
        ('all_users_include_me', 'All Users Including Me'),
        ('role', 'Specific User Type'),
        ('user', 'Specific User'),
    ]

    title = forms.CharField(max_length=255)
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 5}))
    notification_type = forms.ChoiceField(choices=Notification.NOTIFICATION_TYPES, initial='info')
    severity = forms.ChoiceField(choices=Notification.SEVERITY_LEVELS, initial='low')
    target_mode = forms.ChoiceField(choices=TARGET_MODE_CHOICES, initial='all_users')
    target_role = forms.ChoiceField(
        choices=[('', 'Select user type')] + list(User.ROLE_CHOICES),
        required=False,
    )
    target_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('name', 'mobile'),
        required=False,
        empty_label='Select user',
    )

    def clean(self):
        cleaned_data = super().clean()
        target_mode = cleaned_data.get('target_mode')
        target_role = cleaned_data.get('target_role')
        target_user = cleaned_data.get('target_user')

        if target_mode == 'role' and not target_role:
            self.add_error('target_role', 'Please select a user type.')

        if target_mode == 'user' and not target_user:
            self.add_error('target_user', 'Please select a user.')

        return cleaned_data
