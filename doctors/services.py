"""Derived availability: shifts − days off − active bookings."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

from appointments.models import Appointment
from core.jalali import WEEKDAYS_FA

from .models import DoctorProfile

# Persian week starts on Saturday; the model keeps Monday == 0.
PERSIAN_WEEK_ORDER = (5, 6, 0, 1, 2, 3, 4)
WEEKDAY_CHOICES_FA = tuple(
    (weekday, WEEKDAYS_FA[weekday]) for weekday in PERSIAN_WEEK_ORDER
)


def sort_shifts(shifts):
    return sorted(
        shifts,
        key=lambda shift: (
            (shift.weekday + 2) % 7,
            shift.start_time,
        ),
    )

SLOT_DELTA = timedelta(minutes=settings.SLOT_MINUTES)


@dataclass(frozen=True)
class Slot:
    start: time
    end: time

    @property
    def start_str(self) -> str:
        return self.start.strftime("%H:%M")

    @property
    def end_str(self) -> str:
        return self.end.strftime("%H:%M")


def get_doctor_profile(user) -> DoctorProfile:
    """Every doctor-facing page can run even if the profile row is missing."""
    profile, _ = DoctorProfile.objects.get_or_create(
        user=user, defaults={"specialty": "پزشکی عمومی"}
    )
    return profile


def get_free_slots(doctor, day: date, now=None) -> list[Slot]:
    """Expand the doctor's shifts for *day* and drop unavailable starts."""
    now = now or timezone.localtime()
    today = timezone.localdate(now)
    if day < today:
        return []
    if doctor.time_off.filter(date=day).exists():
        return []

    shifts = doctor.working_hours.filter(weekday=day.weekday())
    booked = set(
        doctor.appointments.filter(
            date=day, status=Appointment.Status.BOOKED
        ).values_list("start_time", flat=True)
    )

    is_today = day == today
    now_time = now.time()
    slots: list[Slot] = []
    for shift in shifts:
        cursor = datetime.combine(day, shift.start_time)
        limit = datetime.combine(day, shift.end_time)
        while cursor + SLOT_DELTA <= limit:
            start = cursor.time()
            if start not in booked and not (is_today and start <= now_time):
                slots.append(Slot(start=start, end=(cursor + SLOT_DELTA).time()))
            cursor += SLOT_DELTA
    return sorted(slots, key=lambda slot: slot.start)


def get_shift_slots(doctor, day: date) -> list[Slot]:
    """Every slot a shift defines, ignoring bookings and days off."""
    slots: list[Slot] = []
    for shift in doctor.working_hours.filter(weekday=day.weekday()):
        cursor = datetime.combine(day, shift.start_time)
        limit = datetime.combine(day, shift.end_time)
        while cursor + SLOT_DELTA <= limit:
            slots.append(Slot(cursor.time(), (cursor + SLOT_DELTA).time()))
            cursor += SLOT_DELTA
    return sorted(slots, key=lambda slot: slot.start)


def find_slot(doctor, day: date, start: time, now=None) -> Slot | None:
    return next(
        (slot for slot in get_free_slots(doctor, day, now=now) if slot.start == start),
        None,
    )


def booked_in_shift(doctor, weekday: int, start: time, end: time):
    """Future active appointments that a shift currently covers."""
    appointments = doctor.appointments.filter(
        status=Appointment.Status.BOOKED,
        date__gte=timezone.localdate(),
    ).select_related("patient")
    return [
        appointment
        for appointment in appointments
        if appointment.date.weekday() == weekday
        and start <= appointment.start_time < end
    ]


def booked_on_date(doctor, day: date):
    return doctor.appointments.filter(
        status=Appointment.Status.BOOKED, date=day
    ).select_related("patient")


def upcoming_booked_count(doctor) -> int:
    return doctor.appointments.filter(
        status=Appointment.Status.BOOKED,
        date__gte=timezone.localdate(),
    ).count()
