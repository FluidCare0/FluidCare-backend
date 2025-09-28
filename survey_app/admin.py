from django.contrib import admin

from survey_app.models import DeviceBedAssignmentHistory, PatientBedAssignmentHistory

# ------------------------
# Device Bed Assignment History Admin
# ------------------------
@admin.register(DeviceBedAssignmentHistory)
class DeviceBedAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'device', 'user', 'bed', 'start_time', 'end_time')
    list_filter = ('device', 'user')
    search_fields = ('bed__bed_number', 'user__username')


# ------------------------
# Patient Bed Assignment History Admin
# ------------------------
@admin.register(PatientBedAssignmentHistory)
class PatientBedAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'user', 'bed', 'start_time', 'end_time')
    list_filter = ('patient', 'user')
    search_fields = ('bed__bed_number', 'patient__name', 'user__username')
