from django.contrib import admin
from .models import Patient, Floor, Ward, Bed
from sensor_app.models import DevicePatientAssignment


# ------------------------
# Inline for Device Assignments
# ------------------------
class DeviceAssignmentInline(admin.TabularInline):
    """
    Shows all active/inactive device assignments for a patient directly in Patient admin.
    """
    model = DevicePatientAssignment
    extra = 0
    fields = ('device', 'user', 'start_time', 'end_time', 'notes')
    readonly_fields = ('start_time',)
    autocomplete_fields = ('device', 'user')
    ordering = ('-start_time',)


# ------------------------
# Patient Admin
# ------------------------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at')
    search_fields = ('name', 'contact')
    list_filter = ('gender',)
    readonly_fields = ('id',)
    inlines = [DeviceAssignmentInline]  # 👈 add the inline here


# ------------------------
# Floor Admin
# ------------------------
@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ('id', 'floor_number', 'description')
    search_fields = ('floor_number',)


# ------------------------
# Ward Admin
# ------------------------
@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'ward_number', 'floor')
    search_fields = ('name',)
    list_filter = ('floor',)


# ------------------------
# Bed Admin
# ------------------------
@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('id', 'bed_number', 'ward', 'is_occupied')
    list_filter = ('ward', 'is_occupied')
    search_fields = ('bed_number',)

