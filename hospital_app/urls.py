from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_hospital_structure, name='get_hospital_structure'),
    path('add-floor/', views.add_floor, name='add_floor'),
    path('add-ward/', views.add_ward, name='add_ward'),
    path('add-bed/', views.add_bed, name='add_bed'),
    path('delete-floor/<int:floor_id>/', views.delete_floor, name='delete_floor'),
    path('delete-ward/<int:ward_id>/', views.delete_ward, name='delete_ward'),
    path('delete-bed/<int:bed_id>/', views.delete_bed, name='delete_bed'),
    path('update-bed-status/<int:bed_id>/', views.update_bed_status, name='update_bed_status'),

    path('patients/', views.get_all_patients, name='get_all_patients'),
    path('patients/create/', views.create_patient, name='create_patient'),
    path('patients/<uuid:patient_id>/', views.get_patient_detail, name='get_patient_detail'),
    path('patients/<uuid:patient_id>/discharge/', views.discharge_patient, name='discharge_patient'),
    path('patients/<uuid:patient_id>/assign-bed/', views.assign_patient_to_bed, name='assign_patient_to_bed'),
    path('patients/<uuid:patient_id>/delete/', views.delete_patient, name='delete_patient'),
    path('patients/<uuid:patient_id>/bed-history/', views.get_patient_bed_history, name='get_patient_bed_history'),
    path('patients/<uuid:patient_id>/device-history/', views.get_device_bed_history, name='get_device_bed_history'),
    path('patients/with-history/', views.get_all_patients_with_history, name='get_all_patients_with_history'),
    path('patients/<uuid:patient_id>/related-device-history/', views.get_patient_related_device_history, name='get_patient_related_device_history'),

    path('devices/<int:device_id>/bed-history/', views.get_device_bed_history_by_device_id, name='get_device_bed_history_by_device_id'),

    path('structure/', views.get_hospital_structure, name='get_hospital_structure'),    

]