from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from appointments.emails import send_booking_confirmation
from appointments.forms import BookingForm
from appointments.models import Appointment
from core.jalali import format_jalali, persian_digits
from core.mixins import role_required

from .forms import (
    DoctorProfileForm,
    DoctorSearchForm,
    TimeOffForm,
    WorkingHoursForm,
)
from .models import DoctorProfile
from .services import (
    booked_in_shift,
    booked_on_date,
    find_slot,
    get_doctor_profile,
    get_free_slots,
    sort_shifts,
    upcoming_booked_count,
)


def doctor_list(request):
    form = DoctorSearchForm(request.GET or None)
    doctors = DoctorProfile.objects.select_related("user").prefetch_related(
        "working_hours"
    )
    q = (request.GET.get("q") or "").strip()
    if q:
        doctors = doctors.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(specialty__icontains=q)
            | Q(clinic_name__icontains=q)
        )
    doctors = doctors.annotate(avg_rating=Avg("appointments__review__rating"))
    return render(
        request,
        "doctors/doctor_list.html",
        {"doctors": doctors, "form": form, "q": q},
    )


def _detail_url(doctor, day: date) -> str:
    url = reverse("doctors:detail", args=[doctor.pk])
    return f"{url}?date={day.isoformat()}"


def doctor_detail(request, pk):
    doctor = get_object_or_404(
        DoctorProfile.objects.select_related("user"), pk=pk
    )
    today = timezone.localdate()
    raw_day = request.GET.get("date")
    try:
        day = date.fromisoformat(raw_day or "")
    except (TypeError, ValueError):
        day = today
    if day < today:
        day = today

    slots = get_free_slots(doctor, day)
    selected = None
    raw_start = request.GET.get("start")
    if raw_start:
        try:
            selected_start = time.fromisoformat(raw_start)
        except ValueError:
            selected_start = None
        if selected_start:
            selected = next(
                (slot for slot in slots if slot.start == selected_start), None
            )

    can_book = request.user.is_authenticated and request.user.is_patient
    booking_form = None
    if selected and can_book:
        booking_form = BookingForm(
            initial={"date": day, "start_time": selected.start_str}
        )

    map_url = None
    if doctor.latitude is not None and doctor.longitude is not None:
        map_url = (
            "https://www.openstreetmap.org/"
            f"?mlat={doctor.latitude}&mlon={doctor.longitude}"
            f"#map=16/{doctor.latitude}/{doctor.longitude}"
        )

    context = {
        "doctor": doctor,
        "today": today,
        "day": day,
        "days": [today + timedelta(days=offset) for offset in range(14)],
        "slots": slots,
        "selected": selected,
        "booking_form": booking_form,
        "can_book": can_book,
        "map_url": map_url,
        "weekly_hours": sort_shifts(doctor.working_hours.all()),
    }
    return render(request, "doctors/doctor_detail.html", context)


@login_required
@require_POST
def book(request, pk):
    doctor = get_object_or_404(
        DoctorProfile.objects.select_related("user"), pk=pk
    )
    if not request.user.is_patient:
        messages.error(request, "فقط بیماران می‌توانند نوبت رزرو کنند.")
        return redirect("doctors:detail", pk=doctor.pk)

    form = BookingForm(request.POST)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        posted_day = form.cleaned_data.get("date") or timezone.localdate()
        return redirect(_detail_url(doctor, posted_day))

    day = form.cleaned_data["date"]
    start = form.cleaned_data["start_time"]
    slot = find_slot(doctor, day, start)
    if slot is None:
        messages.error(
            request, "این زمان آزاد نیست؛ ممکن است همین حالا رزرو شده باشد."
        )
        return redirect(_detail_url(doctor, day))

    try:
        with transaction.atomic():
            appointment = Appointment.objects.create(
                patient=request.user,
                doctor=doctor,
                date=day,
                start_time=slot.start,
                end_time=slot.end,
                note=form.cleaned_data["note"],
            )
    except IntegrityError:
        messages.error(
            request, "این زمان همین لحظه توسط بیمار دیگری رزرو شد. زمان دیگری انتخاب کنید."
        )
        return redirect(_detail_url(doctor, day))

    send_booking_confirmation(request, appointment)
    messages.success(
        request,
        f"نوبت شما برای {format_jalali(day, 'full')} "
        f"ساعت {persian_digits(start.strftime('%H:%M'))} ثبت شد.",
    )
    return redirect("appointments:mine")


@role_required("doctor")
def doctor_profile(request):
    profile = get_doctor_profile(request.user)
    form = DoctorProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پروفایل پزشک به‌روزرسانی شد.")
        return redirect("doctor:profile")
    return render(
        request,
        "doctors/profile_form.html",
        {"form": form, "profile": profile},
    )


@role_required("doctor")
def doctor_schedule(request):
    profile = get_doctor_profile(request.user)
    hours = sort_shifts(profile.working_hours.all())
    time_off = profile.time_off.filter(date__gte=timezone.localdate())
    hours_form = WorkingHoursForm(doctor=profile)
    timeoff_form = TimeOffForm()
    pending_timeoff = None
    pending_conflicts = []

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add_hours":
            hours_form = WorkingHoursForm(request.POST, doctor=profile)
            if hours_form.is_valid():
                shift = hours_form.save(commit=False)
                shift.doctor = profile
                shift.save()
                messages.success(request, "شیفت کاری اضافه شد.")
                return redirect("doctor:schedule")
        elif action == "add_timeoff":
            timeoff_form = TimeOffForm(request.POST)
            if timeoff_form.is_valid():
                day = timeoff_form.cleaned_data["date"]
                reason = timeoff_form.cleaned_data["reason"]
                if profile.time_off.filter(date=day).exists():
                    timeoff_form.add_error(
                        "date", "برای این تاریخ قبلاً مرخصی ثبت شده است."
                    )
                else:
                    conflicts = list(booked_on_date(profile, day))
                    if conflicts and request.POST.get("confirm") != "1":
                        pending_timeoff = {
                            "date": day,
                            "reason": reason,
                            "count": len(conflicts),
                        }
                        pending_conflicts = conflicts
                    else:
                        profile.time_off.create(date=day, reason=reason)
                        messages.success(request, "روز مرخصی ثبت شد.")
                        return redirect("doctor:schedule")

    context = {
        "profile": profile,
        "hours": hours,
        "time_off": time_off,
        "upcoming_count": upcoming_booked_count(profile),
        "hours_form": hours_form,
        "timeoff_form": timeoff_form,
        "pending_timeoff": pending_timeoff,
        "pending_conflicts": pending_conflicts,
    }
    return render(request, "doctors/schedule.html", context)


@role_required("doctor")
def doctor_hours_edit(request, pk):
    profile = get_doctor_profile(request.user)
    shift = get_object_or_404(profile.working_hours, pk=pk)
    old = (shift.weekday, shift.start_time, shift.end_time)
    form = WorkingHoursForm(
        request.POST or None, instance=shift, doctor=profile
    )
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        affected = booked_in_shift(profile, *old)
        orphaned = [
            appointment
            for appointment in affected
            if not (
                appointment.date.weekday() == updated.weekday
                and updated.start_time
                <= appointment.start_time
                < updated.end_time
            )
        ]
        if orphaned:
            details = "، ".join(
                f"{appointment.patient.get_full_name() or appointment.patient.username}"
                f" ({format_jalali(appointment.date)}، "
                f"{persian_digits(appointment.start_time.strftime('%H:%M'))})"
                for appointment in orphaned
            )
            form.add_error(
                None,
                "این تغییر نوبت‌های رزروشده را بی‌پوشش می‌کند: "
                f"{details}. ابتدا آن‌ها را لغو یا جابه‌جا کنید.",
            )
        else:
            updated.doctor = profile
            updated.save()
            messages.success(request, "شیفت کاری به‌روزرسانی شد.")
            return redirect("doctor:schedule")
    return render(
        request,
        "doctors/hours_edit.html",
        {"form": form, "shift": shift, "profile": profile},
    )


@role_required("doctor")
@require_POST
def doctor_hours_delete(request, pk):
    profile = get_doctor_profile(request.user)
    shift = get_object_or_404(profile.working_hours, pk=pk)
    conflicts = booked_in_shift(
        profile, shift.weekday, shift.start_time, shift.end_time
    )
    if conflicts:
        details = "، ".join(
            f"{appointment.patient.get_full_name() or appointment.patient.username}"
            f" ({format_jalali(appointment.date)}، "
            f"{persian_digits(appointment.start_time.strftime('%H:%M'))})"
            for appointment in conflicts
        )
        messages.error(
            request,
            "این شیفت نوبت‌های رزروشده دارد و حذف نشد: "
            f"{details}. ابتدا آن‌ها را لغو یا جابه‌جا کنید.",
        )
    else:
        shift.delete()
        messages.success(request, "شیفت کاری حذف شد.")
    return redirect("doctor:schedule")


@role_required("doctor")
@require_POST
def doctor_timeoff_delete(request, pk):
    profile = get_doctor_profile(request.user)
    timeoff = get_object_or_404(profile.time_off, pk=pk)
    timeoff.delete()
    messages.success(request, "روز مرخصی حذف شد.")
    return redirect("doctor:schedule")
