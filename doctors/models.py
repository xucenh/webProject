from django.conf import settings
from django.db import models
from django.db.models import Avg

from core.jalali import format_jalali, persian_digits


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
        limit_choices_to={"role": "doctor"},
        verbose_name="کاربر",
    )
    specialty = models.CharField(max_length=100, verbose_name="تخصص")
    bio = models.TextField(blank=True, verbose_name="درباره من")
    clinic_name = models.CharField(
        max_length=120, blank=True, verbose_name="نام مطب یا کلینیک"
    )
    clinic_address = models.CharField(
        max_length=255, blank=True, verbose_name="نشانی مطب"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="عرض جغرافیایی",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="طول جغرافیایی",
    )
    visit_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="هزینه ویزیت (تومان)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")

    class Meta:
        ordering = ["user__first_name", "user__last_name"]
        verbose_name = "پروفایل پزشک"
        verbose_name_plural = "پروفایل پزشکان"

    def __str__(self) -> str:
        return f"دکتر {self.user.get_full_name() or self.user.username} — {self.specialty}"

    @property
    def average_rating(self):
        return self.appointments.filter(review__isnull=False).aggregate(
            avg=Avg("review__rating")
        )["avg"]


class WorkingHours(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "دوشنبه"
        TUESDAY = 1, "سه‌شنبه"
        WEDNESDAY = 2, "چهارشنبه"
        THURSDAY = 3, "پنج‌شنبه"
        FRIDAY = 4, "جمعه"
        SATURDAY = 5, "شنبه"
        SUNDAY = 6, "یکشنبه"

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="working_hours",
        verbose_name="پزشک",
    )
    weekday = models.IntegerField(
        choices=Weekday.choices, verbose_name="روز هفته"
    )
    start_time = models.TimeField(verbose_name="ساعت شروع")
    end_time = models.TimeField(verbose_name="ساعت پایان")

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name = "شیفت کاری"
        verbose_name_plural = "شیفت‌های کاری"
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
        start = persian_digits(self.start_time.strftime("%H:%M"))
        end = persian_digits(self.end_time.strftime("%H:%M"))
        return f"{self.get_weekday_display()} {start}–{end}"


class TimeOff(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="time_off",
        verbose_name="پزشک",
    )
    date = models.DateField(verbose_name="تاریخ")
    reason = models.CharField(
        max_length=120, blank=True, verbose_name="دلیل"
    )

    class Meta:
        ordering = ["date"]
        verbose_name = "روز مرخصی"
        verbose_name_plural = "روزهای مرخصی"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "date"], name="unique_day_off_per_doctor"
            )
        ]

    def __str__(self) -> str:
        return f"{self.doctor} — مرخصی {format_jalali(self.date, 'short')}"
