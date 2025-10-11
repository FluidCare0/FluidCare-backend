from django.urls import path
from sensor_app import views

urlpatterns = [
    path('dashboard/', views.sensor_dashboard, name='sensor_dashboard'),
    path('devices/', views.get_all_devices, name='get_all_devices'),
]