from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        DOCTOR = "doctor", "پزشک"
        PATIENT = "patient", "بیمار"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.PATIENT,
        verbose_name="نقش",
    )
    email = models.EmailField(unique=True, verbose_name="ایمیل")
    phone = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")

    REQUIRED_FIELDS = ["email"]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_doctor(self) -> bool:
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self) -> bool:
        return self.role == self.Role.PATIENT
