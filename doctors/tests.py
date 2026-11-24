from datetime import time, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from core.jalali import format_jalali
from doctors.models import DoctorProfile, TimeOff, WorkingHours
from doctors.services import get_free_slots

PASSWORD = "Demo12345!"


def make_doctor(username, specialty="قلب و عروق"):
    user = User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=f"{username}@example.com",
        first_name="علی",
        last_name="احمدی",
        role=User.Role.DOCTOR,
        phone="09120000001",
    )
    return DoctorProfile.objects.create(
        user=user,
        specialty=specialty,
        clinic_name="کلینیک مهر",
        clinic_address="تهران",
        visit_fee=350000,
    )


def make_patient(username):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=f"{username}@example.com",
        first_name="سارا",
        last_name="محمدی",
        role=User.Role.PATIENT,
        phone="09120000002",
    )


def next_weekday(weekday):
    day = timezone.localdate() + timedelta(days=1)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return day


class SlotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("doctor_slots")
        WorkingHours.objects.create(
            doctor=cls.doctor,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        cls.monday = next_weekday(0)

    def test_three_hour_shift_has_six_slots(self):
        slots = get_free_slots(self.doctor, self.monday)
        self.assertEqual(len(slots), 6)
        self.assertEqual(slots[0].start_str, "09:00")
        self.assertEqual(slots[-1].start_str, "11:30")
        self.assertEqual(slots[0].end_str, "09:30")

    def test_day_off_removes_every_slot(self):
        TimeOff.objects.create(doctor=self.doctor, date=self.monday)
        self.assertEqual(get_free_slots(self.doctor, self.monday), [])

    def test_booked_slot_is_removed(self):
        Appointment.objects.create(
            patient=make_patient("slot_patient"),
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.BOOKED,
        )
        starts = [slot.start_str for slot in get_free_slots(self.doctor, self.monday)]
        self.assertNotIn("09:00", starts)
        self.assertEqual(len(starts), 5)

    def test_cancelled_slot_stays_free(self):
        Appointment.objects.create(
            patient=make_patient("cancel_patient"),
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.CANCELLED,
        )
        starts = [slot.start_str for slot in get_free_slots(self.doctor, self.monday)]
        self.assertIn("09:00", starts)

    def test_past_date_has_no_slots(self):
        self.assertEqual(
            get_free_slots(self.doctor, timezone.localdate() - timedelta(days=1)),
            [],
        )


class BookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("doctor_book")
        WorkingHours.objects.create(
            doctor=cls.doctor,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        cls.patient = make_patient("patient_one")
        cls.other = make_patient("patient_two")
        cls.monday = next_weekday(0)
        cls.url = reverse("doctors:book", args=[cls.doctor.pk])

    def post_booking(self, start="09:00", note="سردرد"):
        return self.client.post(
            self.url,
            {
                "date": self.monday.isoformat(),
                "start_time": start,
                "note": note,
            },
        )

    def test_patient_books_a_slot(self):
        self.client.force_login(self.patient)
        response = self.post_booking()
        self.assertRedirects(response, reverse("appointments:mine"))
        appointment = Appointment.objects.get(patient=self.patient)
        self.assertEqual(appointment.status, Appointment.Status.BOOKED)
        self.assertEqual(appointment.start_time, time(9, 0))
        self.assertEqual(appointment.end_time, time(9, 30))
        self.assertEqual(appointment.note, "سردرد")

    def test_booking_accepts_jalali_date_input(self):
        self.client.force_login(self.patient)
        response = self.client.post(
            self.url,
            {
                "date": format_jalali(self.monday, "short"),
                "start_time": "09:00",
                "note": "تاریخ شمسی",
            },
        )
        self.assertRedirects(response, reverse("appointments:mine"))
        appointment = Appointment.objects.get(patient=self.patient)
        self.assertEqual(appointment.date, self.monday)

    def test_second_patient_cannot_take_same_slot(self):
        self.client.force_login(self.patient)
        self.post_booking()
        self.client.force_login(self.other)
        response = self.post_booking(start="09:00")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.objects.count(), 1)
        response = self.client.get(response["Location"])
        self.assertContains(response, "آزاد نیست")

    def test_database_refuses_double_booking(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Appointment.objects.create(
                    patient=self.other,
                    doctor=self.doctor,
                    date=self.monday,
                    start_time=time(9, 0),
                    end_time=time(9, 30),
                )

    def test_doctor_cannot_book(self):
        self.client.force_login(self.doctor.user)
        response = self.post_booking()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Appointment.objects.exists())

    def test_slot_outside_shift_is_rejected(self):
        self.client.force_login(self.patient)
        response = self.post_booking(start="13:00")
        self.assertRedirects(
            response, f"{reverse('doctors:detail', args=[self.doctor.pk])}"
            f"?date={self.monday.isoformat()}"
        )
        self.assertFalse(Appointment.objects.exists())

    def test_search_by_specialty_and_name(self):
        response = self.client.get(reverse("doctors:list"), {"q": "قلب"})
        self.assertContains(response, "قلب و عروق")
        response = self.client.get(reverse("doctors:list"), {"q": "احمدی"})
        self.assertContains(response, "دکتر علی احمدی")
        response = self.client.get(reverse("doctors:list"), {"q": "پوست"})
        self.assertNotContains(response, "قلب و عروق")


class ScheduleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("doctor_schedule")
        cls.shift = WorkingHours.objects.create(
            doctor=cls.doctor,
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        cls.patient = make_patient("schedule_patient")
        cls.monday = next_weekday(0)

    def setUp(self):
        self.client.force_login(self.doctor.user)

    def test_add_working_hours(self):
        response = self.client.post(
            reverse("doctor:schedule"),
            {
                "action": "add_hours",
                "weekday": "1",
                "start_time": "14:00",
                "end_time": "16:00",
            },
        )
        self.assertRedirects(response, reverse("doctor:schedule"))
        self.assertTrue(
            WorkingHours.objects.filter(
                doctor=self.doctor, weekday=1, start_time=time(14, 0)
            ).exists()
        )

    def test_overlapping_shift_is_rejected(self):
        response = self.client.post(
            reverse("doctor:schedule"),
            {
                "action": "add_hours",
                "weekday": "0",
                "start_time": "10:00",
                "end_time": "11:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هم‌پوشانی")
        self.assertEqual(
            WorkingHours.objects.filter(doctor=self.doctor, weekday=0).count(), 1
        )

    def test_end_before_start_is_rejected(self):
        response = self.client.post(
            reverse("doctor:schedule"),
            {
                "action": "add_hours",
                "weekday": "1",
                "start_time": "16:00",
                "end_time": "14:00",
            },
        )
        self.assertContains(response, "ساعت پایان باید بعد از ساعت شروع باشد")
        self.assertFalse(WorkingHours.objects.filter(weekday=1).exists())

    def test_delete_shift_with_future_booking_is_refused(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        response = self.client.post(
            reverse("doctor:hours_delete", args=[self.shift.pk]),
            follow=True,
        )
        self.assertContains(response, "نوبت‌های رزروشده دارد")
        self.assertTrue(WorkingHours.objects.filter(pk=self.shift.pk).exists())

    def test_delete_shift_without_bookings(self):
        response = self.client.post(
            reverse("doctor:hours_delete", args=[self.shift.pk])
        )
        self.assertRedirects(response, reverse("doctor:schedule"))
        self.assertFalse(WorkingHours.objects.filter(pk=self.shift.pk).exists())

    def test_day_off_with_booking_requires_confirmation(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        data = {
            "action": "add_timeoff",
            "date": self.monday.isoformat(),
            "reason": "مرخصی",
        }
        response = self.client.post(reverse("doctor:schedule"), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "هشدار")
        self.assertFalse(TimeOff.objects.filter(doctor=self.doctor).exists())

        data["confirm"] = "1"
        response = self.client.post(reverse("doctor:schedule"), data)
        self.assertRedirects(response, reverse("doctor:schedule"))
        self.assertTrue(
            TimeOff.objects.filter(doctor=self.doctor, date=self.monday).exists()
        )

    def test_edit_shift_cannot_orphan_booking(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        response = self.client.post(
            reverse("doctor:hours_edit", args=[self.shift.pk]),
            {
                "weekday": "0",
                "start_time": "10:00",
                "end_time": "12:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "بی‌پوشش")
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.start_time, time(9, 0))

    def test_edit_shift_keeping_booking_is_allowed(self):
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=self.monday,
            start_time=time(9, 0),
            end_time=time(9, 30),
        )
        response = self.client.post(
            reverse("doctor:hours_edit", args=[self.shift.pk]),
            {
                "weekday": "0",
                "start_time": "09:00",
                "end_time": "13:00",
            },
        )
        self.assertRedirects(response, reverse("doctor:schedule"))
        self.shift.refresh_from_db()
        self.assertEqual(self.shift.end_time, time(13, 0))
