from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()

class SendOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    
    def validate_mobile(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Mobile number must include country code (e.g., +91834567890)")
        return value

class VerifyOTPSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6, min_length=6)
    
    def validate_mobile(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Mobile number must include country code")
        return value

class ProfileInfoSerializer(serializers.Serializer):
    name = serializers.CharField(
        required=True,
        min_length=2,
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z ]+$',
                message="Name can only contain letters and spaces"
            )
        ]
    )

    email = serializers.EmailField(
        required=True,
        max_length=100
    )

    class Meta:
        model = User
        fields = ['name', 'email']

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value
    
    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        return instance

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','mobile','name','role', 'email']

class UserManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'mobile', 'name', 'email', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_mobile(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Mobile number must include country code (e.g., +91834567890)")
        return value

    def validate_email(self, value):
        if value:
            if User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
                raise serializers.ValidationError("This email is already registered.")
        return value

class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['mobile', 'name', 'email', 'role', 'is_active']
        read_only_fields = ['created_at', 'updated_at']

    def validate_mobile(self, value):
        if not value.startswith('+'):
            raise serializers.ValidationError("Mobile number must include country code (e.g., +91834567890)")
        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("A user with this mobile number already exists.")
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        # Create user without password
        user = User.objects.create_user(
            mobile=validated_data['mobile'],
            name=validated_data.get('name', ''),
            email=validated_data.get('email', ''),
            role=validated_data.get('role', 'user'),
            is_active=validated_data.get('is_active', True)
        ) # type: ignore
        return user