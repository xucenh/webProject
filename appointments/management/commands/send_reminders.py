from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.emails import send_reminder
from appointments.models import Appointment


class Command(BaseCommand):
    help = "ارسال ایمیل یادآوری برای نوبت‌های ۲۴ ساعت آینده"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="فقط فهرست نوبت‌ها را نشان بده و ایمیلی نفرست",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        until = now + timedelta(hours=24)
        appointments = (
            Appointment.objects.filter(
                status=Appointment.Status.BOOKED,
                date__in=[
                    timezone.localdate(now),
                    timezone.localdate(until),
                ],
            )
            .select_related("patient", "doctor__user")
            .order_by("date", "start_time")
        )
        due = [
            appointment
            for appointment in appointments
            if now <= appointment.starts_at <= until
        ]

        if options["dry_run"]:
            for appointment in due:
                self.stdout.write(
                    f"{appointment.date} {appointment.start_time:%H:%M} — "
                    f"{appointment.patient} / {appointment.doctor}"
                )
            self.stdout.write(f"{len(due)} نوبت در ۲۴ ساعت آینده.")
            return

        for appointment in due:
            send_reminder(appointment)
        self.stdout.write(
            self.style.SUCCESS(f"{len(due)} ایمیل یادآوری ارسال شد.")
        )
