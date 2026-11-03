from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Single auth table for both roles; `role` decides what a user can do.

    Login stays on Django's default `username` field so `createsuperuser`,
    `LoginView` and the admin work without a custom manager. `email` is
    required and unique because confirmations/reminders send mail.
    """

    class Role(models.TextChoices):
        DOCTOR = "doctor", "Doctor"
        PATIENT = "patient", "Patient"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PATIENT)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)

    REQUIRED_FIELDS = ["email"]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_doctor(self) -> bool:
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self) -> bool:
        return self.role == self.Role.PATIENT
