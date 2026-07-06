"""FR-125 — send reminder notifications for upcoming confirmed bookings.

Run via cron now; move to celery-beat when the async layer goes live:
    python manage.py send_due_reminders --window-minutes 60
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.bookings.models import Booking, BookingStatus
from apps.notifications import services as notify


class Command(BaseCommand):
    help = "Send reminders for confirmed bookings starting within the window."

    def add_arguments(self, parser):
        parser.add_argument("--window-minutes", type=int, default=60)

    def handle(self, *args, **options):
        window = timedelta(minutes=options["window_minutes"])
        now = timezone.now()
        due = Booking.objects.filter(
            status=BookingStatus.CONFIRMED,
            reminder_sent_at__isnull=True,
            scheduled_start__gte=now,
            scheduled_start__lte=now + window,
        ).select_related("customer", "vendor")

        count = 0
        for booking in due:
            with transaction.atomic():
                notify.send_push(
                    recipient=booking.customer,
                    title="Appointment reminder",
                    body=f"Your appointment at {booking.vendor.business_name} is coming up.",
                    template_key="booking.reminder",
                )
                booking.reminder_sent_at = now
                booking.save(update_fields=["reminder_sent_at"])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {count} reminder(s)."))
