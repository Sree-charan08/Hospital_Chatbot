from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from app1.models import Encounter

class Command(BaseCommand):
    help = 'Process upcoming follow-up appointments and send reminders'

    def handle(self, *args, **options):
        # Get all follow-up appointments scheduled for the next 7 days
        next_week = timezone.now() + timezone.timedelta(days=7)
        upcoming_follow_ups = Encounter.objects.filter(
            visit_type='FU',  # Follow-up visits
            status='BOOKED',
            visit_date__gte=timezone.now(),
            visit_date__lte=next_week
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {upcoming_follow_ups.count()} upcoming follow-up appointments')
        )
        
        for encounter in upcoming_follow_ups:
            # Send reminder to patient
            self.send_follow_up_reminder(encounter)
            
        self.stdout.write(
            self.style.SUCCESS('Successfully processed all upcoming follow-up appointments')
        )
    
    def send_follow_up_reminder(self, encounter):
        # Prepare message content
        message = f'''
Follow-up Appointment Reminder

Dear {encounter.patient.first_name} {encounter.patient.last_name},

This is a reminder for your upcoming follow-up appointment:

Appointment ID: {encounter.encounter_id}
Doctor: Dr. {encounter.doctor.first_name} {encounter.doctor.last_name} ({encounter.doctor.specialization})
Date & Time: {encounter.visit_date.strftime('%Y-%m-%d %H:%M')}
Reason: {encounter.problem or 'Follow-up consultation'}

Please confirm your attendance and let us know if you need to reschedule.

Contact us if you have any questions.

Best regards,
Hospital Administration
        '''.strip()
        
        # Send email reminder if patient has email
        if encounter.patient.email:
            try:
                send_mail(
                    f'Reminder: Upcoming Follow-up Appointment #{encounter.encounter_id}',
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hospital.com'),
                    [encounter.patient.email],
                    fail_silently=False,
                )
                self.stdout.write(
                    f'Sent follow-up reminder to {encounter.patient.email} for appointment {encounter.encounter_id}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send email to {encounter.patient.email}: {e}')
                )
        
        # Print reminder to console for phone calls
        self.stdout.write(
            f'Follow-up reminder for {encounter.patient.first_name} {encounter.patient.last_name} '
            f'(Phone: {encounter.patient.phone}) for appointment {encounter.encounter_id}'
        )