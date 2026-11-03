from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg


class DoctorProfile(models.Model):
    """Extra data for users whose `role` is `doctor` (1:1 with the auth user)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        limit_choices_to={"role": "doctor"},
    )
    specialty = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    clinic_name = models.CharField(max_length=120, blank=True)
    clinic_address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    visit_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self) -> str:
        return f"Dr. {self.user.get_full_name() or self.user.username} — {self.specialty}"

    @property
    def average_rating(self):
        """Computed from reviews, never stored, so it cannot go stale."""
        return self.appointments.filter(review__isnull=False).aggregate(
            avg=Avg("review__rating")
        )["avg"]


class WorkingHours(models.Model):
    """Recurring weekly availability; the source for generated slots."""

    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name="working_hours"
    )
    weekday = models.IntegerField(choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="working_hours_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["doctor", "weekday", "start_time"],
                name="unique_shift_per_doctor",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"


class TimeOff(models.Model):
    """One-off exception to the weekly pattern (holiday, sick day)."""

    doctor = models.ForeignKey(
        DoctorProfile, on_delete=models.CASCADE, related_name="time_off"
    )
    date = models.DateField()
    reason = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date"], name="unique_day_off_per_doctor"
            )
        ]

    def __str__(self) -> str:
        return f"{self.doctor} off on {self.date:%Y-%m-%d}"
