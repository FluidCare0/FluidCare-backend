from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, mobile, name, role, password=None, **extra_fields):
        if not mobile:
            raise ValueError("Mobile number is required")
        user = self.model(mobile=mobile, name=name, role=role, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile, name, password=None, **extra_fields):
        if not password:
            raise ValueError("Superuser must have a password")
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(mobile, name, role='root_admin', password=password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('root_admin', 'Root Admin'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('lab_technician', 'Lab Technician'),
        ('receptionist', 'Receptionist'),
        ('manager', 'Manager'),
        ('user', 'User'), 
    ]

    mobile            = models.CharField(max_length=15, unique=True, db_index=True)
    name              = models.CharField(max_length=100, null=True, blank=True, default='empty')
    email             = models.EmailField(null=True, blank=True, db_index=True)
    is_email_verified = models.BooleanField(default=False)
    role              = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    is_active         = models.BooleanField(default=True)
    is_staff          = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

    def __str__(self):
        return f"{self.name} ({self.mobile})"

    class Meta:
        indexes = [
            models.Index(fields=['role', 'is_active']),
        ]