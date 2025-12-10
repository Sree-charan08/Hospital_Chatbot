from django.db import models

# Create your models here.

# -------------------------
# PATIENT
# -------------------------
class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    patient_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    allergies = models.TextField(blank=True, null=True)  # Free text input

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


# -------------------------
# DOCTOR
# -------------------------
class Doctor(models.Model):
    doctor_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)

    def __str__(self):
        return f"Dr. {self.first_name} {self.last_name} ({self.specialization})"


# -------------------------
# ENCOUNTERS (Visits)
# -------------------------
class Encounter(models.Model):
    VISIT_TYPES = [
        ('OPD', 'Outpatient'),
        ('IPD', 'Inpatient Admission'),
        ('ER', 'Emergency'),
        ('FU', 'Follow-Up'),
        ('TELE', 'Teleconsultation'),
    ]

    encounter_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="encounters")
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    visit_type = models.CharField(max_length=10, choices=VISIT_TYPES)
    visit_date = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    # Minimal appointment lifecycle fields
    status = models.CharField(max_length=20, default='BOOKED')
    payment_status = models.CharField(max_length=20, default='PENDING')
    problem = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Encounter {self.encounter_id} - {self.patient}"


# -------------------------
# REMINDERS
# -------------------------
class Reminder(models.Model):
    reminder_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='reminders')
    remind_at = models.DateTimeField()
    method = models.CharField(max_length=20, default='CALL')
    # Add health check field
    health_check_required = models.BooleanField(default=False)
    health_check_done = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder {self.reminder_id} for {self.encounter}"


# -------------------------
# FEEDBACK
# -------------------------
class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField(null=True, blank=True)
    comments = models.TextField(blank=True, null=True)
    follow_up_required = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback {self.feedback_id} for {self.encounter}"


# -------------------------
# MEDICATIONS
# -------------------------
class Medication(models.Model):
    medication_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medications")
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="medications")
    name = models.CharField(max_length=100)
    dosage = models.CharField(max_length=50)
    frequency = models.CharField(max_length=50)  # e.g., "Twice a day"
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name


# -------------------------
# LAB RESULTS
# -------------------------
class LabResult(models.Model):
    lab_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="lab_results")
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True)
    test_name = models.CharField(max_length=100)
    result_value = models.CharField(max_length=100)
    result_unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    test_date = models.DateField()

    def __str__(self):
        return f"{self.test_name} - {self.patient}"


# -------------------------
# ALLERGIES
# -------------------------
class Allergy(models.Model):
    allergy_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="allergy_list")
    allergen = models.CharField(max_length=100)
    reaction = models.CharField(max_length=200)
    severity = models.CharField(max_length=50)

    def __str__(self):
        return self.allergen


# -------------------------
# IMMUNIZATIONS
# -------------------------
class Immunization(models.Model):
    imm_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="immunizations")
    vaccine_name = models.CharField(max_length=100)
    date_given = models.DateField()
    dose_number = models.IntegerField()

    def __str__(self):
        return self.vaccine_name


# -------------------------
# DIAGNOSES
# -------------------------
class Diagnosis(models.Model):
    diag_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="diagnoses")
    diagnosis_code = models.CharField(max_length=20)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description


# -------------------------
# VITAL SIGNS
# -------------------------
class Vital(models.Model):
    vital_id = models.AutoField(primary_key=True)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, related_name="vitals")
    temperature = models.FloatField()
    heart_rate = models.IntegerField()
    blood_pressure = models.CharField(max_length=20)  # e.g., "120/80"
    oxygen_saturation = models.IntegerField()
    recorded_at = models.DateTimeField()

    def __str__(self):
        return f"Vitals for {self.encounter}"


# -------------------------
# INSURANCE
# -------------------------
class Insurance(models.Model):
    insurance_id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="insurance")
    provider_name = models.CharField(max_length=100)
    policy_number = models.CharField(max_length=50)
    coverage_start = models.DateField()
    coverage_end = models.DateField()

    def __str__(self):
        return self.provider_name
