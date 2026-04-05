from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from .models import User

# ---- Forms ----
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('mobile', 'name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.cleaned_data.get('password1'):
            user.set_unusable_password()
        else:
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

# ---- Admin ----
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = ('mobile', 'name', 'email', 'role', 'is_active', 'is_staff', 'is_email_verified', 'created_at')
    list_filter = ('role', 'is_active', 'is_staff', 'is_email_verified')
    search_fields = ('mobile', 'name', 'email')
    ordering = ('-created_at',)

    # Make non-editable fields read-only
    readonly_fields = ('last_login', 'created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('mobile', 'password')}),
        ('Personal Info', {'fields': ('name', 'email')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_email_verified', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile', 'name', 'email', 'role', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')}
        ),
    )

admin.site.register(User, UserAdmin)

admin.site.site_header = "FluidCare Administration"
admin.site.site_title = "FluidCare Admin"
admin.site.index_title = "Welcome to FluidCare Management Portal"
