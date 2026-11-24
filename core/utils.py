from django.urls import reverse


def role_landing(user) -> str:
    """FR-06: doctors land on their dashboard, patients on the doctor list."""
    if getattr(user, "is_doctor", False):
        return reverse("doctor:appointments")
    return reverse("doctors:list")
