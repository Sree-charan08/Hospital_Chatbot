from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
from datetime import datetime, timedelta, time
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from .models import Patient, Doctor, Encounter, Reminder, Feedback
from django.conf import settings
from . import llm


def index(request):
	return render(request, 'chat.html')


def map_symptom_to_specialization(problem_text: str) -> str:
	# Prefer LLM-based classification if GROQ key is configured
	try:
		if getattr(settings, 'GROQ_API_KEY', ''):
			spec = llm.classify_specialization(problem_text)
			if spec:
				return spec
	except Exception:
		# fall back to rule-based mapping on any LLM error
		pass

	text = problem_text.lower()
	if any(k in text for k in ['chest', 'heart', 'bp', 'breath']):
		return 'Cardiology'
	if any(k in text for k in ['bone', 'joint', 'fracture']):
		return 'Orthopedics'
	if any(k in text for k in ['fever', 'stomach', 'weak', 'cold', 'flu']):
		return 'General Medicine'
	if any(k in text for k in ['rash', 'itch', 'skin', 'allergy']):
		return 'Dermatology'
	if any(k in text for k in ['ear', 'nose', 'throat']):
		return 'ENT'
	if any(k in text for k in ['preg', 'period', 'women']):
		return 'Gynecology'
	if any(k in text for k in ['child', 'kid', 'children']):
		return 'Pediatrics'
	return 'General Medicine'


def find_doctor_for_specialization(spec: str):
	return Doctor.objects.filter(specialization__iexact=spec).first()


def choose_appointment_slot(doctor):
	# Choose same-day next hour slot between 09:00-17:00 if available, else 2 days later
	now = timezone.localtime()
	start_hour = max(now.hour + 1, 9)
	if start_hour > 17:
		candidate = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0, microsecond=0)
	else:
		candidate = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)

	# check conflict exact datetime; if exists, move 2 days later same time
	conflict = Encounter.objects.filter(doctor=doctor, visit_date=candidate).exists()
	if conflict:
		candidate = candidate + timedelta(days=2)
	return candidate


def get_available_slots(doctor, days_ahead=7):
	"""Get available slots for a doctor for the next few days"""
	slots = []
	now = timezone.localtime()
	
	# Generate slots for the next 7 days
	for day_offset in range(days_ahead):
		date = now + timedelta(days=day_offset)
		
		# Skip Sundays (assuming 6 = Sunday in weekday())
		if date.weekday() == 6:
			continue
			
		# Generate time slots between 9 AM and 5 PM
		for hour in range(9, 18):
			slot_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
			
			# Skip past times for today
			if day_offset == 0 and slot_time < now:
				continue
				
			# Check if slot is available
			conflict = Encounter.objects.filter(doctor=doctor, visit_date=slot_time).exists()
			if not conflict:
				slots.append(slot_time)
				
			# Limit to reasonable number of slots
			if len(slots) >= 10:
				break
		
		if len(slots) >= 10:
			break
			
	return slots


@csrf_exempt
def perform_action(request):
	if request.method != 'POST':
		return HttpResponseBadRequest('POST required')

	try:
		payload = json.loads(request.body.decode('utf-8'))
	except Exception:
		return HttpResponseBadRequest('Invalid JSON')

	action = payload.get('action')
	data = payload.get('data', {})

	if action == 'REGISTER_PATIENT':
		required = ['first_name', 'last_name', 'dob', 'gender', 'phone', 'blood_group']
		for r in required:
			if r not in data:
				return JsonResponse({'error': f'Missing field {r}'}, status=400)
		p = Patient.objects.create(
			first_name=data['first_name'],
			last_name=data['last_name'],
			dob=data['dob'],
			gender=data['gender'],
			phone=data['phone'],
			blood_group=data.get('blood_group'),
			address=data.get('address', ''),
			email=data.get('email')
		)
		return JsonResponse({'action': 'REGISTER_PATIENT', 'patient_id': p.patient_id})

	if action == 'VALIDATE_PATIENT':
		pid = data.get('patient_id')
		phone = data.get('phone')
		patient = None
		if pid:
			patient = Patient.objects.filter(patient_id=pid).first()
		elif phone:
			patient = Patient.objects.filter(phone=phone).first()
		if not patient:
			return JsonResponse({'action': 'VALIDATE_PATIENT', 'valid': False})
		
		# Get patient's previous encounters
		previous_encounters = []
		encounters = Encounter.objects.filter(patient=patient).order_by('-visit_date')
		for enc in encounters:
			previous_encounters.append({
				'encounter_id': enc.encounter_id,
				'doctor_name': f"Dr. {enc.doctor.first_name} {enc.doctor.last_name}" if enc.doctor else "Unknown",
				'specialization': enc.doctor.specialization if enc.doctor else "Unknown",
				'visit_date': enc.visit_date.isoformat(),
				'problem': enc.problem,
				'status': enc.status
			})
		
		return JsonResponse({'action': 'VALIDATE_PATIENT', 'valid': True, 'patient': {
			'patient_id': patient.patient_id,
			'first_name': patient.first_name,
			'last_name': patient.last_name,
			'phone': patient.phone,
		}, 'previous_encounters': previous_encounters})

	if action == 'ASSIGN_DOCTOR':
		problem = data.get('problem')
		if not problem:
			return JsonResponse({'error': 'problem required'}, status=400)
		spec = map_symptom_to_specialization(problem)
		doc = find_doctor_for_specialization(spec)
		if not doc:
			return JsonResponse({'action': 'ASSIGN_DOCTOR', 'assigned': False, 'specialization': spec})
		
		# Get available slots for this doctor
		slots = get_available_slots(doc)
		slot_options = []
		for i, slot in enumerate(slots[:5]):  # Show first 5 slots
			slot_options.append({
				'id': i+1,
				'datetime': slot.isoformat(),
				'date': slot.strftime('%Y-%m-%d'),
				'time': slot.strftime('%H:%M')
			})
		
		return JsonResponse({'action': 'ASSIGN_DOCTOR', 'assigned': True, 'doctor': {
			'doctor_id': doc.doctor_id,
			'first_name': doc.first_name,
			'last_name': doc.last_name,
			'specialization': doc.specialization,
		}, 'available_slots': slot_options})

	if action == 'CREATE_ENCOUNTER' or action == 'BOOK_APPOINTMENT':
		patient_id = data.get('patient_id')
		doctor_id = data.get('doctor_id')
		problem = data.get('problem')
		previous_encounter_id = data.get('previous_encounter_id')
		slot_choice = data.get('slot_choice')  # Optional slot choice
		
		if not patient_id or not doctor_id or not problem:
			return JsonResponse({'error': 'patient_id, doctor_id, problem required'}, status=400)
		patient = get_object_or_404(Patient, pk=patient_id)
		doctor = get_object_or_404(Doctor, pk=doctor_id)
		
		# Use chosen slot or default slot selection
		if slot_choice:
			try:
				appt_dt = datetime.fromisoformat(slot_choice)
			except ValueError:
				return JsonResponse({'error': 'Invalid slot choice'}, status=400)
		else:
			appt_dt = choose_appointment_slot(doctor)
		
		# Determine visit type based on whether it's a follow-up
		visit_type = 'FU' if previous_encounter_id else 'OPD'
		
		enc = Encounter.objects.create(
			patient=patient,
			doctor=doctor,
			visit_type=visit_type,
			visit_date=appt_dt,
			notes=problem,
			problem=problem,
			status='BOOKED',
			payment_status='PENDING',
		)

		# create reminder 24 hours prior if appointment not same-day
		remind_at = appt_dt - timedelta(hours=24)
		Reminder.objects.create(
			encounter=enc, 
			remind_at=remind_at, 
			method='CALL',
			health_check_required=True
		)

		return JsonResponse({'action': action, 'encounter': {
			'encounter_id': enc.encounter_id,
			'appointment_date': enc.visit_date.isoformat(),
			'appointment_time': enc.visit_date.time().isoformat(),
			'status': enc.status,
			'visit_type': enc.visit_type,
		}})

	if action == 'SEND_EMAIL':
		encounter_id = data.get('encounter_id')
		if not encounter_id:
			return JsonResponse({'error': 'encounter_id required'}, status=400)
		
		encounter = get_object_or_404(Encounter, pk=encounter_id)
		
		# Debug: Print email settings
		import os
		print("EMAIL_HOST:", getattr(settings, 'EMAIL_HOST', 'Not set'))
		print("EMAIL_HOST_USER:", getattr(settings, 'EMAIL_HOST_USER', 'Not set'))
		print("EMAIL_HOST_PASSWORD length:", len(getattr(settings, 'EMAIL_HOST_PASSWORD', '')))
		print("DEFAULT_FROM_EMAIL:", getattr(settings, 'DEFAULT_FROM_EMAIL', 'Not set'))
		
		# Prepare email content
		subject = f'Hospital Appointment Confirmation - OP#{encounter.encounter_id}'
		
		# Create email message
		message = f'''
Dear {encounter.patient.first_name} {encounter.patient.last_name},

Your appointment has been confirmed with the following details:

Appointment ID: {encounter.encounter_id}
Doctor: Dr. {encounter.doctor.first_name} {encounter.doctor.last_name} ({encounter.doctor.specialization})
Date & Time: {encounter.visit_date.strftime('%Y-%m-%d %H:%M')}
Type: {'Follow-up Visit' if encounter.visit_type == 'FU' else 'New Outpatient Visit'}
Concern: {encounter.problem}

Please arrive 15 minutes early for registration.

Payment Status: {encounter.payment_status}

If you need to reschedule or cancel, please contact us at least 24 hours in advance.

Thank you for choosing our hospital.

Best regards,
Hospital Administration
		'''.strip()
		
		# Send email if patient has email address
		if encounter.patient.email:
			try:
				# Check if email settings are properly configured
				if not getattr(settings, 'EMAIL_HOST', None) or getattr(settings, 'EMAIL_HOST') == 'localhost':
					error_message = "Email server not properly configured. Please check EMAIL_HOST settings."
					print(f"Email configuration error: {error_message}")
					return JsonResponse({
						'action': 'SEND_EMAIL', 
						'sent': False, 
						'patient_email': encounter.patient.email,
						'error': error_message
					})
				
				send_mail(
					subject,
					message,
					getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hospital.com'),
					[encounter.patient.email],
					fail_silently=False,
				)
				email_sent = True
				error_message = None
			except Exception as e:
				# Log error but don't fail the request
				error_message = str(e)
				print(f"Failed to send email: {e}")
				email_sent = False
		else:
			email_sent = False
			error_message = "No email address provided for patient"
		
		response_data = {
			'action': 'SEND_EMAIL', 
			'sent': email_sent, 
			'patient_email': encounter.patient.email or 'N/A'
		}
		
		if error_message:
			response_data['error'] = error_message
			
		return JsonResponse(response_data)

	if action == 'SCHEDULE_REMINDER':
		encounter_id = data.get('encounter_id')
		remind_at = data.get('remind_at')
		if not encounter_id or not remind_at:
			return JsonResponse({'error': 'encounter_id and remind_at required'}, status=400)
		enc = get_object_or_404(Encounter, pk=encounter_id)
		try:
			dt = datetime.fromisoformat(remind_at)
		except Exception:
			return JsonResponse({'error': 'invalid remind_at format'}, status=400)
		Reminder.objects.create(encounter=enc, remind_at=dt, method=data.get('method', 'CALL'))
		return JsonResponse({'action': 'SCHEDULE_REMINDER', 'scheduled': True})

	if action == 'POST_VISIT_FEEDBACK':
		encounter_id = data.get('encounter_id')
		rating = data.get('rating')
		comments = data.get('comments')
		follow_up = data.get('follow_up_required', False)
		if not encounter_id:
			return JsonResponse({'error': 'encounter_id required'}, status=400)
		enc = get_object_or_404(Encounter, pk=encounter_id)
		fb = Feedback.objects.create(encounter=enc, rating=rating, comments=comments, follow_up_required=follow_up)
		
		# Send feedback summary to patient
		if enc.patient.email:
			try:
				subject = f'Visit Summary - Appointment #{encounter_id}'
				message = f'''
Dear {enc.patient.patient.first_name} {enc.patient.patient.last_name},

Thank you for visiting our hospital. Here's a summary of your visit:

Appointment ID: {encounter_id}
Doctor: Dr. {enc.doctor.first_name} {enc.doctor.last_name} ({enc.doctor.specialization})
Date & Time: {enc.visit_date.strftime('%Y-%m-%d %H:%M')}
Concern: {enc.problem}

Your Feedback:
Rating: {rating}/5
Comments: {comments or 'None provided'}

We'll follow up with you shortly if needed.

Best regards,
Hospital Administration
				'''.strip()
				
				send_mail(
					subject,
					message,
					getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hospital.com'),
					[enc.patient.email],
					fail_silently=False,
				)
			except Exception as e:
				print(f"Failed to send feedback summary: {e}")
		
		return JsonResponse({'action': 'POST_VISIT_FEEDBACK', 'feedback_id': fb.feedback_id})
	
	if action == 'GET_VISIT_SUMMARY':
		encounter_id = data.get('encounter_id')
		if not encounter_id:
			return JsonResponse({'error': 'encounter_id required'}, status=400)
		
		enc = get_object_or_404(Encounter, pk=encounter_id)
		
		# Get all related information
		medications = []
		for med in enc.medications.all():
			medications.append({
				'name': med.name,
				'dosage': med.dosage,
				'frequency': med.frequency,
				'start_date': med.start_date.isoformat(),
				'end_date': med.end_date.isoformat() if med.end_date else None,
			})
		
		diagnoses = []
		for diag in enc.diagnoses.all():
			diagnoses.append({
				'code': diag.diagnosis_code,
				'description': diag.description,
			})
		
		vitals = []
		for vital in enc.vitals.all():
			vitals.append({
				'temperature': vital.temperature,
				'heart_rate': vital.heart_rate,
				'blood_pressure': vital.blood_pressure,
				'oxygen_saturation': vital.oxygen_saturation,
				'recorded_at': vital.recorded_at.isoformat(),
			})
		
		lab_results = []
		for lab in enc.lab_results.all():
			lab_results.append({
				'test_name': lab.test_name,
				'result_value': lab.result_value,
				'result_unit': lab.result_unit,
				'reference_range': lab.reference_range,
				'test_date': lab.test_date.isoformat(),
			})
		
		# Get feedback if exists
		feedback = None
		if hasattr(enc, 'feedbacks') and enc.feedbacks.exists():
			fb = enc.feedbacks.first()
			feedback = {
				'rating': fb.rating,
				'comments': fb.comments,
				'follow_up_required': fb.follow_up_required,
			}
		
		summary = {
			'encounter_id': enc.encounter_id,
			'patient': {
				'patient_id': enc.patient.patient_id,
				'first_name': enc.patient.first_name,
				'last_name': enc.patient.last_name,
				'dob': enc.patient.dob.isoformat(),
				'gender': enc.patient.gender,
				'email': enc.patient.email,
				'phone': enc.patient.phone,
				'blood_group': enc.patient.blood_group,
			},
			'doctor': {
				'doctor_id': enc.doctor.doctor_id,
				'first_name': enc.doctor.first_name,
				'last_name': enc.doctor.last_name,
				'specialization': enc.doctor.specialization,
			},
			'visit_details': {
				'visit_type': enc.visit_type,
				'visit_date': enc.visit_date.isoformat(),
				'problem': enc.problem,
				'notes': enc.notes,
				'status': enc.status,
				'payment_status': enc.payment_status,
			},
			'medications': medications,
			'diagnoses': diagnoses,
			'vitals': vitals,
			'lab_results': lab_results,
			'feedback': feedback,
		}
		
		return JsonResponse({'action': 'GET_VISIT_SUMMARY', 'summary': summary})
	
	if action == 'UPDATE_PAYMENT_STATUS':
		encounter_id = data.get('encounter_id')
		payment_status = data.get('payment_status')
		if not encounter_id or not payment_status:
			return JsonResponse({'error': 'encounter_id and payment_status required'}, status=400)
		enc = get_object_or_404(Encounter, pk=encounter_id)
		enc.payment_status = payment_status
		enc.save()
		return JsonResponse({'action': 'UPDATE_PAYMENT_STATUS', 'updated': True})
	
	if action == 'SCHEDULE_FOLLOW_UP':
		encounter_id = data.get('encounter_id')
		follow_up_days = data.get('follow_up_days', 7)  # Default to 7 days
		reason = data.get('reason', 'Follow-up consultation')
		
		if not encounter_id:
			return JsonResponse({'error': 'encounter_id required'}, status=400)
		
		enc = get_object_or_404(Encounter, pk=encounter_id)
		
		# Schedule follow-up appointment
		follow_up_date = timezone.now() + timedelta(days=follow_up_days)
		
		# Find next available slot with the same doctor
		doctor = enc.doctor
		if not doctor:
			return JsonResponse({'error': 'No doctor found for this encounter'}, status=400)
		
		# Try to find an available slot
		appt_dt = choose_appointment_slot(doctor)
		
		# Create follow-up encounter
		follow_up_enc = Encounter.objects.create(
			patient=enc.patient,
			doctor=doctor,
			visit_type='FU',  # Follow-up
			visit_date=appt_dt,
			notes=reason,
			problem=reason,
			status='BOOKED',
			payment_status='PENDING',
		)
		
		# Create reminder for follow-up
		remind_at = appt_dt - timedelta(hours=24)
		Reminder.objects.create(
			encounter=follow_up_enc, 
			remind_at=remind_at, 
			method='CALL',
			health_check_required=True
		)
		
		# Send confirmation to patient
		if enc.patient.email:
			try:
				subject = f'Follow-up Appointment Scheduled - #{follow_up_enc.encounter_id}'
				message = f'''
Dear {enc.patient.first_name} {enc.patient.last_name},

A follow-up appointment has been scheduled for you:

Appointment ID: {follow_up_enc.encounter_id}
Doctor: Dr. {doctor.first_name} {doctor.last_name} ({doctor.specialization})
Date & Time: {follow_up_enc.visit_date.strftime('%Y-%m-%d %H:%M')}
Reason: {reason}

Please confirm your attendance.

Best regards,
Hospital Administration
				'''.strip()
				
				send_mail(
					subject,
					message,
					getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hospital.com'),
					[enc.patient.email],
					fail_silently=False,
				)
			except Exception as e:
				print(f"Failed to send follow-up confirmation: {e}")
		
		return JsonResponse({
			'action': 'SCHEDULE_FOLLOW_UP', 
			'follow_up_encounter_id': follow_up_enc.encounter_id,
			'appointment_date': follow_up_enc.visit_date.isoformat()
		})
	
	if action == 'CHECK_FOLLOW_UP_STATUS':
		patient_id = data.get('patient_id')
		if not patient_id:
			return JsonResponse({'error': 'patient_id required'}, status=400)
		
		# Get all upcoming follow-ups for this patient
		upcoming_follow_ups = Encounter.objects.filter(
			patient_id=patient_id,
			visit_type='FU',
			status='BOOKED',
			visit_date__gte=timezone.now()
		).order_by('visit_date')
		
		follow_ups = []
		for enc in upcoming_follow_ups:
			follow_ups.append({
				'encounter_id': enc.encounter_id,
				'doctor_name': f"Dr. {enc.doctor.first_name} {enc.doctor.last_name}" if enc.doctor else "Unknown",
				'specialization': enc.doctor.specialization if enc.doctor else "Unknown",
				'visit_date': enc.visit_date.isoformat(),
				'reason': enc.problem,
			})
		
		return JsonResponse({
			'action': 'CHECK_FOLLOW_UP_STATUS',
			'follow_ups': follow_ups
		})
	
	if action == 'LIST_DOCTORS':
		# Get all doctors
		doctors = Doctor.objects.all()
		doctor_list = []
		for doc in doctors:
			doctor_list.append({
				'doctor_id': doc.doctor_id,
				'first_name': doc.first_name,
				'last_name': doc.last_name,
				'specialization': doc.specialization,
			})
		
		return JsonResponse({
			'action': 'LIST_DOCTORS',
			'doctors': doctor_list
		})
	
	if action == 'GET_PATIENT_HISTORY':
		patient_id = data.get('patient_id')
		if not patient_id:
			return JsonResponse({'error': 'patient_id required'}, status=400)
		
		# Get patient's previous encounters
		previous_encounters = []
		encounters = Encounter.objects.filter(patient_id=patient_id).order_by('-visit_date')
		for enc in encounters:
			previous_encounters.append({
				'encounter_id': enc.encounter_id,
				'doctor_name': f"Dr. {enc.doctor.first_name} {enc.doctor.last_name}" if enc.doctor else "Unknown",
				'specialization': enc.doctor.specialization if enc.doctor else "Unknown",
				'visit_date': enc.visit_date.isoformat(),
				'problem': enc.problem,
				'status': enc.status
			})
		
		return JsonResponse({
			'action': 'GET_PATIENT_HISTORY',
			'history': previous_encounters
		})
	
	if action == 'GET_LAB_REPORTS':
		patient_id = data.get('patient_id')
		if not patient_id:
			return JsonResponse({'error': 'patient_id required'}, status=400)
		
		# Get patient's lab results
		lab_results = []
		results = LabResult.objects.filter(patient_id=patient_id).order_by('-test_date')
		for result in results:
			lab_results.append({
				'test_name': result.test_name,
				'result_value': result.result_value,
				'result_unit': result.result_unit,
				'reference_range': result.reference_range,
				'test_date': result.test_date.isoformat(),
			})
		
		return JsonResponse({
			'action': 'GET_LAB_REPORTS',
			'reports': lab_results
		})
	
	return JsonResponse({'error': 'unknown action'}, status=400)
