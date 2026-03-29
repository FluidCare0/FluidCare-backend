from django.contrib import admin
from .models import Patient, Floor, Ward, Bed



# ------------------------
# Patient Admin
# ------------------------
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'age', 'gender', 'contact', 'admitted_at', 'discharged_at')
    search_fields = ('name', 'contact')
    list_filter = ('gender',)
    readonly_fields = ('id',)



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
    list_editable = ('is_occupied',)


