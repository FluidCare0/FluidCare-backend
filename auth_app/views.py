from rest_framework import status, permissions, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone

from .serializers import (
            SendOTPSerializer, VerifyOTPSerializer, 
            UserSerializer, ProfileInfoSerializer,
            UserManagementSerializer, CreateUserSerializer,
)

from .utils import send_otp, verify_otp

User = get_user_model()



class VerifyOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            mobile = serializer.validated_data['mobile']
            otp = serializer.validated_data['otp']

            if not verify_otp(mobile, otp):
                return Response({
                    "detail": "Invalid or expired OTP."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user
            user, created = User.objects.get_or_create(
                mobile=mobile,
                defaults={'role': 'user'},
            )

            needs_profile_completion = user.name == 'empty'

            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)


            response = Response({
                'access': access_token,
                'user': UserSerializer(user).data,
                'needs_profile_completion': needs_profile_completion
            }, status=status.HTTP_200_OK)

            # Set refresh token in HttpOnly cookie
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Lax',
                max_age=7 * 24 * 60 * 60,  # 7 days
                path='/'
            )

            return response
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileInfoView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        serializer = ProfileInfoSerializer(
            instance=request.user,
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "user": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(views.APIView):
    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            response = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
            response.delete_cookie('refresh_token', path='/')
            return response
        except Exception as e:
            response = Response({"detail": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST)
            response.delete_cookie('refresh_token', path='/')
            return response

class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            return Response({
                "detail": "Refresh token not found in cookies"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        request.data['refresh'] = refresh_token
        
        try:
            response = super().post(request, *args, **kwargs)

            if hasattr(settings, 'SIMPLE_JWT') and settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS', False):
                if 'refresh' in response.data:
                    response.set_cookie(
                        key='refresh_token',
                        value=response.data['refresh'],
                        httponly=True,
                        secure=not settings.DEBUG,
                        samesite='Lax',
                        max_age=7 * 24 * 60 * 60,  
                        path='/'
                    )
            
            return response
            
        except Exception as e:
            return Response({
                "detail": f"Token refresh failed: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

class SendOTPView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    
    @method_decorator(ratelimit(key='post:mobile', rate='3/10m', method='POST'))
    @method_decorator(ratelimit(key='ip', rate='10/h', method='POST'))
    def post(self, request):
        if getattr(request, 'limited', False):
            return Response({
                "detail": "Too many OTP requests. Please try again later."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            try:
                mobile = serializer.validated_data['mobile']
                send_otp(mobile)
                return Response({
                    "detail": "OTP sent successfully"
                }, status=status.HTTP_200_OK)
                
            except AttributeError as e:
                return Response({
                    "detail": f"Server configuration error: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except Exception as e:
                return Response({
                    "detail": f"Failed to send OTP: {str(e)}"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
class CurrentUserView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data) 

class UserListView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Only root_admin and manager can view users
        if request.user.role not in ['root_admin', 'manager']:
            return Response({
                "detail": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        # Filter users based on role hierarchy
        if request.user.role == 'root_admin':
            users = User.objects.all()
        else:  # manager
            users = User.objects.exclude(role='root_admin')

        # Apply filters from query params
        role = request.query_params.get('role', None)
        status_param = request.query_params.get('status', None)
        search = request.query_params.get('search', None)

        if role:
            users = users.filter(role=role)
        if status_param == 'active':
            users = users.filter(is_active=True)
        elif status_param == 'inactive':
            users = users.filter(is_active=False)
        if search:
            users = users.filter(
                name__icontains=search
            ) | users.filter(
                mobile__icontains=search
            ) | users.filter(
                email__icontains=search
            )

        serializer = UserManagementSerializer(users, many=True)
        return Response({
            "users": serializer.data,
            "count": len(serializer.data)
        })

class UserCreateView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ['root_admin', 'manager']:
            return Response({
                "detail": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        # Managers can only create users with role 'user'
        if request.user.role == 'manager' and request.data.get('role') != 'user':
            return Response({
                "detail": "Managers can only create users with 'user' role"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully",
                "user": UserManagementSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        if request.user.role not in ['root_admin', 'manager']:
            return Response({
                "detail": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        user = get_object_or_404(User, pk=pk)
        
        # Check if user can access this user
        if request.user.role == 'manager' and user.role == 'root_admin':
            return Response({
                "detail": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = UserManagementSerializer(user)
        return Response(serializer.data)

class UserUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        if request.user.role not in ['root_admin', 'manager']:
            return Response({
                "detail": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        user = get_object_or_404(User, pk=pk)
        
        # Managers have restricted update capabilities
        if request.user.role == 'manager':
            # 1. Managers cannot update other managers or root admins
            if user.role in ['root_admin', 'manager']:
                return Response({
                    "detail": "Permission denied - managers cannot update other managers or root admins"
                }, status=status.HTTP_403_FORBIDDEN)

            # 2. Managers can only update specific fields. 
            # We filter the incoming data instead of rejecting the request if extra fields (like id, mobile) are present.
            allowed_fields = {'name', 'email', 'is_active'}
            
            # Special case: allow mobile if it hasn't changed
            if 'mobile' in request.data and request.data['mobile'] == user.mobile:
                # We don't add it to filtered_data because we don't want to trigger unnecessary validation/save
                pass
            
            filtered_data = {k: v for k, v in request.data.items() if k in allowed_fields}
            serializer = UserManagementSerializer(user, data=filtered_data, partial=True)
        else:
            # Root admins can update everything
            serializer = UserManagementSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "User updated successfully",
                "user": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if request.user.role != 'root_admin':
            return Response({
                "detail": "Permission denied - only root admin can delete users"
            }, status=status.HTTP_403_FORBIDDEN)

        user = get_object_or_404(User, pk=pk)
        
        # Root admin cannot delete themselves
        if user.id == request.user.id:
            return Response({
                "detail": "Cannot delete yourself"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.delete()
        return Response({
            "message": "User deleted successfully"
        }, status=status.HTTP_204_NO_CONTENT)