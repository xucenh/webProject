from datetime import date, datetime
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import User
from appointments.models import Appointment
from core.forms import JalaliDateField
from core.jalali import (
    format_jalali,
    jalali_to_gregorian,
    persian_digits,
    to_jalali,
    weekday_fa,
)
from doctors.models import DoctorProfile


class JalaliTests(SimpleTestCase):
    def test_known_conversions(self):
        self.assertEqual(to_jalali(date(2024, 3, 20)), (1403, 1, 1))
        self.assertEqual(to_jalali(date(2025, 3, 21)), (1404, 1, 1))
        self.assertEqual(to_jalali(date(2026, 3, 21)), (1405, 1, 1))
        self.assertEqual(to_jalali(date(2026, 11, 23)), (1405, 9, 2))

    def test_persian_formatting(self):
        self.assertEqual(format_jalali(date(2026, 11, 23)), "۲ آذر ۱۴۰۵")
        self.assertEqual(
            format_jalali(date(2026, 11, 23), "full"),
            "دوشنبه ۲ آذر ۱۴۰۵",
        )
        self.assertEqual(
            format_jalali(datetime(2026, 11, 23, 14, 30), "datetime"),
            "۲ آذر ۱۴۰۵، ساعت ۱۴:۳۰",
        )
        self.assertEqual(persian_digits("09:05"), "۰۹:۰۵")
        self.assertEqual(weekday_fa(0), "دوشنبه")
        self.assertEqual(weekday_fa(date(2026, 11, 23)), "دوشنبه")

    def test_reverse_conversion(self):
        self.assertEqual(
            jalali_to_gregorian(1405, 9, 2), date(2026, 11, 23)
        )
        self.assertEqual(
            jalali_to_gregorian(1403, 1, 1), date(2024, 3, 20)
        )
        self.assertEqual(
            jalali_to_gregorian(1403, 12, 30), date(2025, 3, 20)
        )


class JalaliDateFieldTests(SimpleTestCase):
    def test_accepts_persian_and_latin_jalali_digits(self):
        field = JalaliDateField()
        expected = date(2026, 11, 28)
        self.assertEqual(field.to_python("۱۴۰۵/۰۹/۰۷"), expected)
        self.assertEqual(field.to_python("1405/09/07"), expected)
        self.assertEqual(field.to_python("1405-09-07"), expected)

    def test_still_accepts_iso_gregorian(self):
        field = JalaliDateField()
        self.assertEqual(field.to_python("2026-11-28"), date(2026, 11, 28))

    def test_rejects_invalid_jalali_dates(self):
        field = JalaliDateField()
        for value in ("۱۴۰۵/۱۳/۰۱", "۱۴۰۵/۱۲/۳۱", "۱۴۰۵/۰۰/۱۰"):
            with self.assertRaises(ValidationError):
                field.to_python(value)

    def test_prepares_persian_value(self):
        field = JalaliDateField()
        self.assertEqual(field.prepare_value(date(2026, 11, 28)), "۱۴۰۵/۰۹/۰۷")


class HomeTests(TestCase):
    def test_home_is_persian_and_rtl(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="fa"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "کلینیک مهر")


class SeedDemoTests(TestCase):
    def test_seed_is_idempotent(self):
        out = StringIO()
        call_command("seed_demo", stdout=out)
        self.assertEqual(DoctorProfile.objects.count(), 5)
        self.assertEqual(User.objects.filter(role=User.Role.PATIENT).count(), 4)
        booked = Appointment.objects.filter(
            status=Appointment.Status.BOOKED
        ).count()
        self.assertGreater(booked, 0)

        call_command("seed_demo", stdout=out)
        self.assertEqual(DoctorProfile.objects.count(), 5)
        self.assertEqual(
            Appointment.objects.filter(status=Appointment.Status.BOOKED).count(),
            booked,
        )
