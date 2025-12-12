from django.contrib import admin
from .models import Device, DevicePatientAssignment, FluidBag, SensorReading

# ------------------------
# SensorReading Inline
# ------------------------
class SensorReadingInline(admin.TabularInline):
    model = SensorReading
    extra = 0  # do not show extra empty forms
    readonly_fields = ('reading', 'timestamp', )
    can_delete = False  # prevent deletion from inline (optional)


# ------------------------
# FluidBag Admin
# ------------------------
@admin.register(FluidBag)
class FluidBagAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'device', 'capacity_ml', 'threshold_low', 'threshold_high')
    list_filter = ('type', 'device')
    search_fields = ('device__mac_address', 'type')
    inlines = [SensorReadingInline]
    readonly_fields = ('id',)


# ------------------------
# Device Admin
# ------------------------
@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'mac_address', 'type',  'installed_at')
    list_filter = ('type', )
    search_fields = ('mac_address',)
    readonly_fields = ('id', 'installed_at')


# ------------------------
# SensorReading Admin
# ------------------------
@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('id', 'fluid_bag', 'reading', 'timestamp')
    list_filter = ('fluid_bag', )
    search_fields = ('fluidBag__device__mac_address',)
    readonly_fields = ('reading', 'timestamp', )

@admin.register(DevicePatientAssignment)
class DevicePatientAssignmentAdmin(admin.ModelAdmin):
    list_display = ('device', 'fluid', 'patient', 'user', 'start_time', 'end_time', 'is_active')
    list_filter = ('end_time', 'user')
    search_fields = ('device__mac_address', 'patient__name', 'user__username')
    ordering = ('-start_time',)
    autocomplete_fields = ('device', 'patient', 'user')
    readonly_fields = ('start_time',)

    def is_active(self, obj):
        return obj.end_time is None
    is_active.boolean = True
    is_active.short_description = "Active"