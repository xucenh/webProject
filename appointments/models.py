from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class Appointment(models.Model):
    """A single booking; one doctor + one date + one start_time while active.

    Slots are never stored: they are computed from the doctor's WorkingHours
    minus TimeOff minus active appointments. The partial unique constraint is
    what actually prevents double booking (cancelled rows are excluded, so a
    freed slot can be booked again).
    """

    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        limit_choices_to={"role": "patient"},
    )
    doctor = models.ForeignKey(
        "doctors.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.BOOKED
    )
    note = models.TextField(blank=True, help_text="Reason for the visit (optional).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["doctor", "date"], name="appt_doctor_date_idx"),
            models.Index(fields=["patient", "date"], name="appt_patient_date_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date", "start_time"],
                condition=Q(status="booked"),
                name="unique_active_slot_per_doctor",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="appointment_end_after_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.patient} → {self.doctor} on {self.date:%Y-%m-%d} {self.start_time:%H:%M}"


class Review(models.Model):
    """Bonus: one rating per completed appointment."""

    appointment = models.OneToOneField(
        Appointment, on_delete=models.CASCADE, related_name="review"
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.rating}/5 for {self.appointment.doctor}"
