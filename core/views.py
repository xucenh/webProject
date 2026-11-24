from django.shortcuts import render

from appointments.models import Appointment
from doctors.models import DoctorProfile


def home(request):
    doctors = (
        DoctorProfile.objects.select_related("user")
        .prefetch_related("working_hours")
        .order_by("-created_at")[:3]
    )
    context = {
        "doctors": doctors,
        "doctor_count": DoctorProfile.objects.count(),
        "booked_count": Appointment.objects.filter(
            status=Appointment.Status.BOOKED
        ).count(),
    }
    return render(request, "home.html", context)
