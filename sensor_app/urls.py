from django.urls import path
from sensor_app import views

urlpatterns = [
    path('dashboard/', views.sensor_dashboard, name='sensor_dashboard'),
]