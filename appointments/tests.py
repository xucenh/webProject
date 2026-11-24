from datetime import time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment, Review
from doctors.models import DoctorProfile

PASSWORD = "Demo12345!"


def make_doctor(username):
    user = User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=f"{username}@example.com",
        first_name="علی",
        last_name="احمدی",
        role=User.Role.DOCTOR,
    )
    return DoctorProfile.objects.create(user=user, specialty="قلب")


def make_patient(username):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=f"{username}@example.com",
        first_name="سارا",
        last_name="محمدی",
        role=User.Role.PATIENT,
        phone="09120000000",
    )


class CancelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("cancel_doctor")
        cls.patient = make_patient("cancel_owner")
        cls.other = make_patient("cancel_other")
        cls.appointment = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=timezone.localdate() + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )

    def test_owner_cancels_and_slot_is_released(self):
        self.client.force_login(self.patient)
        response = self.client.post(
            reverse("appointments:cancel", args=[self.appointment.pk])
        )
        self.assertRedirects(response, reverse("appointments:mine"))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)

    def test_other_patient_gets_404(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("appointments:cancel", args=[self.appointment.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.BOOKED)

    def test_completed_appointment_cannot_be_cancelled(self):
        self.appointment.status = Appointment.Status.COMPLETED
        self.appointment.save()
        self.client.force_login(self.patient)
        response = self.client.post(
            reverse("appointments:cancel", args=[self.appointment.pk]),
            follow=True,
        )
        self.assertContains(response, "فقط نوبت‌های رزروشده")
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)


class ReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("review_doctor")
        cls.patient = make_patient("review_owner")
        cls.other = make_patient("review_other")
        cls.completed = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=timezone.localdate() - timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(9, 30),
            status=Appointment.Status.COMPLETED,
        )
        cls.booked = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=timezone.localdate() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(10, 30),
        )

    def test_review_is_refused_for_booked_appointment(self):
        self.client.force_login(self.patient)
        response = self.client.get(
            reverse("appointments:review", args=[self.booked.pk])
        )
        self.assertRedirects(response, reverse("appointments:mine"))
        self.assertFalse(Review.objects.exists())

    def test_patient_reviews_completed_appointment_once(self):
        self.client.force_login(self.patient)
        url = reverse("appointments:review", args=[self.completed.pk])
        response = self.client.post(
            url, {"rating": "5", "comment": "ویزیت عالی بود"}
        )
        self.assertRedirects(response, reverse("appointments:mine"))
        review = Review.objects.get(appointment=self.completed)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "ویزیت عالی بود")

        self.client.post(url, {"rating": "1", "comment": "تلاش دوم"})
        self.assertEqual(Review.objects.count(), 1)
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)

    def test_existing_review_is_shown_read_only(self):
        Review.objects.create(
            appointment=self.completed, rating=4, comment="خوب بود"
        )
        self.client.force_login(self.patient)
        response = self.client.get(
            reverse("appointments:review", args=[self.completed.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قبلاً ثبت شده")
        self.assertContains(response, "خوب بود")

    def test_other_patient_gets_404(self):
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("appointments:review", args=[self.completed.pk])
        )
        self.assertEqual(response.status_code, 404)


class CompletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doctor = make_doctor("complete_doctor")
        cls.other_doctor = make_doctor("other_doctor")
        cls.patient = make_patient("complete_patient")
        cls.past = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=timezone.localdate() - timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(9, 30),
            note="یادداشت محرمانه",
        )
        cls.future = Appointment.objects.create(
            patient=cls.patient,
            doctor=cls.doctor,
            date=timezone.localdate() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(9, 30),
        )

    def test_future_visit_cannot_be_completed(self):
        self.client.force_login(self.doctor.user)
        response = self.client.post(
            reverse("doctor:complete_appointment", args=[self.future.pk]),
            follow=True,
        )
        self.assertContains(response, "تا زمان ویزیت نگذشته")
        self.future.refresh_from_db()
        self.assertEqual(self.future.status, Appointment.Status.BOOKED)

    def test_past_visit_can_be_completed(self):
        self.client.force_login(self.doctor.user)
        response = self.client.post(
            reverse("doctor:complete_appointment", args=[self.past.pk])
        )
        self.assertRedirects(response, reverse("doctor:appointments"))
        self.past.refresh_from_db()
        self.assertEqual(self.past.status, Appointment.Status.COMPLETED)

    def test_other_doctor_cannot_complete_or_see_appointment(self):
        self.client.force_login(self.other_doctor.user)
        response = self.client.post(
            reverse("doctor:complete_appointment", args=[self.past.pk])
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.get(reverse("doctor:appointments"))
        self.assertNotContains(response, "یادداشت محرمانه")
