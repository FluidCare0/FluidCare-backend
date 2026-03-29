# sensor_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import Device, FluidBag, SensorReading, PatientDeviceBedAssignment
from django.utils.html import format_html

# --- Inline for Fluid Bags ---
class FluidBagInline(admin.TabularInline):
    model = FluidBag
    extra = 0
    fields = ('type', 'capacity_ml', 'threshold_low', 'threshold_high')
    readonly_fields = ('type', 'capacity_ml', 'threshold_low', 'threshold_high')

# --- Inline for Sensor Readings (optional for detail view) ---
class SensorReadingInline(admin.TabularInline):
    model = SensorReading
    extra = 0
    readonly_fields = ('reading', 'timestamp')
    ordering = ('-timestamp',)

# --- Device Admin ---
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('mac_address', 'type', 'status', 'stop_at', 'removed_from_dashboard')
    list_filter = ('status', 'type')
    search_fields = ('mac_address',)
    inlines = [FluidBagInline]
    ordering = ('-created_at',)

# --- Main Assignment Admin ---
@admin.register(PatientDeviceBedAssignment)
class PatientDeviceBedAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'patient_name',
        'device_mac',
        'bed_number',
        'ward_name',
        'floor_number',
        'is_active',
        'started',
        'ended',
        'active_duration'
    )
    list_filter = ('ward', 'floor', 'end_time')
    search_fields = ('patient__name', 'device__mac_address', 'bed__bed_number', 'ward__name')
    readonly_fields = ('start_time', 'end_time', 'ward', 'floor')
    list_per_page = 25

    fieldsets = (
        ("Assignment Info", {
            "fields": (
                "patient", "device", "bed", "ward", "floor", "user", "notes"
            ),
        }),
        ("Timeline", {
            "fields": ("start_time", "end_time"),
        }),
    )

    def patient_name(self, obj):
        return obj.patient.name
    patient_name.short_description = "Patient"

    def device_mac(self, obj):
        mac = obj.device.mac_address if obj.device else "No Device"
        return format_html("<b>{}</b>", mac)
    
    def bed_number(self, obj):
        return obj.bed.bed_number if obj.bed else "-"
    bed_number.short_description = "Bed"

    def ward_name(self, obj):
        return obj.ward.name if obj.ward else "-"
    ward_name.short_description = "Ward"

    def floor_number(self, obj):
        return obj.floor.floor_number if obj.floor else "-"
    floor_number.short_description = "Floor"

    def started(self, obj):
        return obj.start_time.strftime("%Y-%m-%d %H:%M") if obj.start_time else "-"
    started.short_description = "Start Time"

    def ended(self, obj):
        if obj.end_time:
            return format_html(
                '<span style="color:#999;">{}</span>',
                obj.end_time.strftime("%Y-%m-%d %H:%M")
            )
        return format_html('<b style="color:green;">Active</b>')
    ended.short_description = "End Time"

    def is_active(self, obj):
        return obj.end_time is None
    is_active.boolean = True
    is_active.short_description = "Active"

    def active_duration(self, obj):
        if obj.end_time:
            duration = obj.end_time - obj.start_time
        else:
            duration = timezone.now() - obj.start_time

        hours = duration.total_seconds() / 3600
        color = "#007BFF" if not obj.end_time else "#555"
        formatted_hours = f"{hours:.1f}"
        return format_html('<span style="color:{};">{} hr</span>', color, formatted_hours)

# --- Optional: FluidBag Admin (standalone view) ---
@admin.register(FluidBag)
class FluidBagAdmin(admin.ModelAdmin):
    list_display = ('device', 'type', 'capacity_ml', 'threshold_low', 'threshold_high')
    search_fields = ('device__mac_address', 'type')
    list_filter = ('type',)
