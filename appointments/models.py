from datetime import datetime

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from core.jalali import format_jalali, persian_digits


class Appointment(models.Model):

    class Status(models.TextChoices):
        BOOKED = "booked", "رزروشده"
        COMPLETED = "completed", "انجام‌شده"
        CANCELLED = "cancelled", "لغوشده"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        limit_choices_to={"role": "patient"},
        verbose_name="بیمار",
    )
    doctor = models.ForeignKey(
        "doctors.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="پزشک",
    )
    date = models.DateField(verbose_name="تاریخ")
    start_time = models.TimeField(verbose_name="ساعت شروع")
    end_time = models.TimeField(verbose_name="ساعت پایان")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.BOOKED,
        verbose_name="وضعیت",
    )
    note = models.TextField(
        blank=True,
        verbose_name="توضیح بیمار",
        help_text="دلیل مراجعه (اختیاری).",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="آخرین به‌روزرسانی"
    )

    class Meta:
        ordering = ["date", "start_time"]
        verbose_name = "نوبت"
        verbose_name_plural = "نوبت‌ها"
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
        start = persian_digits(self.start_time.strftime("%H:%M"))
        return (
            f"{self.patient} → {self.doctor} "
            f"در {format_jalali(self.date, 'short')} ساعت {start}"
        )

    @property
    def starts_at(self):
        """Timezone-aware start instant, used to gate completing a visit."""
        return timezone.make_aware(datetime.combine(self.date, self.start_time))


class Review(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="review",
        verbose_name="نوبت",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="امتیاز",
    )
    comment = models.TextField(blank=True, verbose_name="نظر")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"

    def __str__(self) -> str:
        return f"امتیاز {persian_digits(self.rating)} از ۵ برای {self.appointment.doctor}"
