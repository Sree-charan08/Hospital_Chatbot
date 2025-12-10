from django.contrib import admin

# Register your models here.
from .models import (
    Patient, Doctor, Encounter, Medication, LabResult,
    Allergy, Immunization, Diagnosis, Vital, Insurance
)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("patient_id", "first_name", "last_name", "dob", "gender", "phone", "blood_group")
    search_fields = ("first_name", "last_name", "phone")


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("doctor_id", "first_name", "last_name", "specialization")
    search_fields = ("first_name", "last_name", "specialization")


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ("encounter_id", "patient", "doctor", "visit_type", "visit_date", "notes")
    list_filter = ("visit_type", "doctor")
    search_fields = ("patient__first_name", "patient__last_name")


admin.site.register(Medication)
admin.site.register(LabResult)
admin.site.register(Allergy)
admin.site.register(Immunization)
admin.site.register(Diagnosis)
admin.site.register(Vital)
admin.site.register(Insurance)
