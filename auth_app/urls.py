from django.urls import path
from .views import (
            SendOTPView, VerifyOTPView, 
            LogoutView, CookieTokenRefreshView,
            ProfileInfoView, CurrentUserView,
            UserListView, UserDetailView, 
            UserCreateView,UserUpdateView, 
            UserDeleteView
        )

urlpatterns = [
    path('send-otp/', SendOTPView.as_view()),
    path('verify-otp/', VerifyOTPView.as_view()),
    path('refresh/', CookieTokenRefreshView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('profile-info/', ProfileInfoView.as_view()),
    path('user/', CurrentUserView.as_view()),

    path('users/', UserListView.as_view(), name='user-list'),
    
    path('users/create/', UserCreateView.as_view(), name='user-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user-update'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),
]
