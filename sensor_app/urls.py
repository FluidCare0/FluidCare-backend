from django.urls import path
from sensor_app import views

urlpatterns = [
    path('dashboard/', views.sensor_dashboard, name='sensor_dashboard'),
    path('devices/', views.get_all_devices, name='get_all_devices'),
    path('sensor/devices/<uuid:device_id>/remove-from-dashboard/', views.remove_device_from_dashboard, name='remove-device-dashboard'),
    path('devices/<uuid:device_id>/patient-details/', views.get_patient_details_by_device, name='get-patient-details-by-device'),
    path('devices/<uuid:device_id>/patient-history/', views.get_patient_assignment_history_by_device, name='get-patient-history-by-device'),
    path('devices/<uuid:device_id>/device-history/', views.get_device_assignment_history, name='get-device-history'),
    path('sensor/devices/<uuid:device_id>/history/', views.get_sensor_history, name='get_sensor_history'),
    path('devices/register/', views.register_node, name="register_node")

]