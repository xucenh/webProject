from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.mixins import role_required
from doctors.services import get_doctor_profile

from .emails import (
    send_cancellation_notice,
    send_review_invitation,
)
from .forms import ReviewForm
from .models import Appointment, Review


@role_required("patient")
def my_appointments(request):
    appointments = list(
        Appointment.objects.filter(patient=request.user)
        .select_related("doctor__user")
        .prefetch_related("review")
        .order_by("date", "start_time")
    )
    reviewed = set(
        Review.objects.filter(appointment__in=appointments).values_list(
            "appointment_id", flat=True
        )
    )
    today = timezone.localdate()
    upcoming, past = [], []
    for appointment in appointments:
        appointment.can_review = (
            appointment.status == Appointment.Status.COMPLETED
            and appointment.pk not in reviewed
        )
        if (
            appointment.status == Appointment.Status.BOOKED
            and appointment.date >= today
        ):
            upcoming.append(appointment)
        else:
            past.append(appointment)

    return render(
        request,
        "appointments/my_appointments.html",
        {"upcoming": upcoming, "past": past},
    )


@role_required("patient")
@require_POST
def cancel(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor__user"),
        pk=pk,
        patient=request.user,
    )
    if appointment.status != Appointment.Status.BOOKED:
        messages.error(request, "فقط نوبت‌های رزروشده قابل لغو هستند.")
    else:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])
        send_cancellation_notice(appointment)
        messages.success(request, "نوبت شما لغو شد و زمان آن آزاد شد.")
    return redirect("appointments:mine")


@role_required("patient")
def review(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related("doctor__user"),
        pk=pk,
        patient=request.user,
    )
    if appointment.status != Appointment.Status.COMPLETED:
        messages.error(request, "ثبت نظر فقط برای ویزیت‌های تکمیل‌شده ممکن است.")
        return redirect("appointments:mine")

    existing = Review.objects.filter(appointment=appointment).first()
    if existing:
        return render(
            request,
            "appointments/review_form.html",
            {"appointment": appointment, "review": existing, "form": None},
        )

    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review_obj = form.save(commit=False)
        review_obj.appointment = appointment
        try:
            review_obj.save()
        except IntegrityError:
            messages.error(request, "برای این ویزیت قبلاً نظر ثبت شده است.")
        else:
            messages.success(request, "نظر شما ثبت شد. سپاس از همراهی!")
        return redirect("appointments:mine")

    return render(
        request,
        "appointments/review_form.html",
        {"appointment": appointment, "review": None, "form": form},
    )


@role_required("doctor")
def doctor_appointments(request):
    profile = get_doctor_profile(request.user)
    appointments = list(
        profile.appointments.select_related("patient")
        .prefetch_related("review")
        .order_by("-date", "-start_time")
    )
    now = timezone.now()
    for appointment in appointments:
        appointment.can_complete = (
            appointment.status == Appointment.Status.BOOKED
            and appointment.starts_at <= now
        )
    return render(
        request,
        "appointments/doctor_appointments.html",
        {"appointments": appointments, "profile": profile},
    )


@role_required("doctor")
@require_POST
def complete_appointment(request, pk):
    profile = get_doctor_profile(request.user)
    appointment = get_object_or_404(
        profile.appointments.select_related("patient"), pk=pk
    )
    if appointment.status != Appointment.Status.BOOKED:
        messages.error(request, "این نوبت در وضعیت رزروشده نیست.")
    elif appointment.starts_at > timezone.now():
        messages.error(request, "تا زمان ویزیت نگذشته، تکمیل آن ممکن نیست.")
    else:
        appointment.status = Appointment.Status.COMPLETED
        appointment.save(update_fields=["status", "updated_at"])
        send_review_invitation(request, appointment)
        messages.success(
            request, "ویزیت تکمیل شد و دعوت به ثبت نظر برای بیمار ارسال شد."
        )
    return redirect("doctor:appointments")
