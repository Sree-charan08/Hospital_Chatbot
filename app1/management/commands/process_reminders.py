from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from app1.models import Reminder

class Command(BaseCommand):
    help = 'Process pending reminders and send health check calls'

    def handle(self, *args, **options):
        # Get all pending reminders that are due
        now = timezone.now()
        pending_reminders = Reminder.objects.filter(
            remind_at__lte=now,
            health_check_done=False
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Found {pending_reminders.count()} pending reminders')
        )
        
        for reminder in pending_reminders:
            # Process the reminder
            self.process_reminder(reminder)
            
        self.stdout.write(
            self.style.SUCCESS('Successfully processed all pending reminders')
        )
    
    def process_reminder(self, reminder):
        # Mark the health check as done
        reminder.health_check_done = True
        reminder.save()
        
        # Prepare message content
        message = f'''
Health Check Reminder

Dear {reminder.encounter.patient.first_name} {reminder.encounter.patient.last_name},

This is a reminder for your upcoming appointment:

Appointment ID: {reminder.encounter.encounter_id}
Doctor: Dr. {reminder.encounter.doctor.first_name} {reminder.encounter.doctor.last_name}
Date & Time: {reminder.encounter.visit_date.strftime('%Y-%m-%d %H:%M')}

Please confirm your attendance and let us know if you have any health concerns before the visit.

Contact us if you need to reschedule.

Best regards,
Hospital Administration
        '''.strip()
        
        # Send SMS or make call (placeholder)
        if reminder.method == 'CALL':
            self.stdout.write(
                f'Making call to {reminder.encounter.patient.phone} for appointment {reminder.encounter.encounter_id}'
            )
            # In a real implementation, you would integrate with a telephony service here
            
        # Also send email reminder if patient has email
        if reminder.encounter.patient.email:
            try:
                send_mail(
                    f'Reminder: Upcoming Appointment #{reminder.encounter.encounter_id}',
                    message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@hospital.com'),
                    [reminder.encounter.patient.email],
                    fail_silently=False,
                )
                self.stdout.write(
                    f'Sent email reminder to {reminder.encounter.patient.email}'
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to send email: {e}')
                )