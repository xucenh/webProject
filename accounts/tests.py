from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from doctors.models import DoctorProfile

PASSWORD = "Demo12345!"


def make_user(username, role, email=None, **extra):
    return User.objects.create_user(
        username=username,
        password=PASSWORD,
        email=email or f"{username}@example.com",
        role=role,
        **extra,
    )


class SignupTests(TestCase):
    def test_patient_signup_creates_patient_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "role": "patient",
                "first_name": "سارا",
                "last_name": "محمدی",
                "username": "sara_new",
                "email": "sara_new@example.com",
                "phone": "09120000000",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("doctors:list"))
        user = User.objects.get(username="sara_new")
        self.assertEqual(user.role, User.Role.PATIENT)
        self.assertEqual(user.email, "sara_new@example.com")
        self.assertIn("_auth_user_id", self.client.session)

    def test_doctor_signup_creates_profile(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "role": "doctor",
                "first_name": "علی",
                "last_name": "احمدی",
                "username": "dr_new",
                "email": "dr_new@example.com",
                "phone": "09120000001",
                "specialty": "قلب و عروق",
                "clinic_name": "کلینیک مهر",
                "clinic_address": "تهران",
                "visit_fee": "350000",
                "bio": "متخصص قلب",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("doctor:appointments"))
        user = User.objects.get(username="dr_new")
        self.assertEqual(user.role, User.Role.DOCTOR)
        self.assertEqual(user.doctor_profile.specialty, "قلب و عروق")
        self.assertEqual(str(user.doctor_profile.visit_fee), "350000.00")

    def test_doctor_signup_requires_specialty(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "role": "doctor",
                "first_name": "علی",
                "last_name": "احمدی",
                "username": "dr_bad",
                "email": "dr_bad@example.com",
                "phone": "09120000002",
                "clinic_name": "کلینیک",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="dr_bad").exists())
        self.assertContains(response, "تخصص الزامی است")

    def test_email_must_be_unique(self):
        make_user("existing", User.Role.PATIENT, email="same@example.com")
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "role": "patient",
                "first_name": "سارا",
                "last_name": "محمدی",
                "username": "another",
                "email": "same@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertContains(response, "این ایمیل قبلاً ثبت شده است")
        self.assertFalse(User.objects.filter(username="another").exists())


class LoginTests(TestCase):
    def test_patient_login_lands_on_doctor_list(self):
        make_user("patient1", User.Role.PATIENT)
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "patient1", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("doctors:list"))

    def test_doctor_login_lands_on_dashboard(self):
        user = make_user("doctor1", User.Role.DOCTOR)
        DoctorProfile.objects.create(user=user, specialty="قلب")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "doctor1", "password": PASSWORD},
        )
        self.assertRedirects(response, reverse("doctor:appointments"))

    def test_role_guard_returns_403(self):
        user = make_user("doctor2", User.Role.DOCTOR)
        DoctorProfile.objects.create(user=user, specialty="قلب")
        self.client.force_login(user)
        response = self.client.get(reverse("appointments:mine"))
        self.assertEqual(response.status_code, 403)
