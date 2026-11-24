"""Create a realistic Persian demo clinic.

Run ``python manage.py seed_demo`` for an idempotent top-up, or
``python manage.py seed_demo --reset`` to delete and recreate only the demo
accounts and their data.
"""

from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment, Review
from doctors.models import DoctorProfile, TimeOff, WorkingHours
from doctors.services import get_shift_slots

DEMO_PASSWORD = "Demo12345!"

DOCTORS = [
    {
        "username": "dr_ahmadi",
        "first_name": "علی",
        "last_name": "احمدی",
        "email": "ahmadi@clinic.example",
        "phone": "09121110001",
        "specialty": "قلب و عروق",
        "clinic_name": "کلینیک قلب مهر",
        "clinic_address": "تهران، خیابان ولیعصر، پلاک ۱۲۰",
        "latitude": "35.744800",
        "longitude": "51.409900",
        "visit_fee": "350000",
        "bio": "متخصص قلب و عروق با بیش از ۱۵ سال تجربه در تشخیص و درمان بیماری‌های قلبی.",
        "hours": [
            (5, time(9, 0), time(13, 0)),
            (0, time(16, 0), time(20, 0)),
            (2, time(9, 0), time(13, 0)),
        ],
    },
    {
        "username": "dr_sadeghi",
        "first_name": "مریم",
        "last_name": "صادقی",
        "email": "sadeghi@clinic.example",
        "phone": "09121110002",
        "specialty": "پوست، مو و زیبایی",
        "clinic_name": "مطب دکتر صادقی",
        "clinic_address": "تهران، سعادت‌آباد، بلوار دریا، پلاک ۴۵",
        "latitude": "35.783900",
        "longitude": "51.371200",
        "visit_fee": "280000",
        "bio": "متخصص پوست و مو؛ درمان آکنه، ریزش مو و بیماری‌های پوستی.",
        "hours": [
            (6, time(10, 0), time(14, 0)),
            (1, time(10, 0), time(14, 0)),
            (3, time(16, 0), time(20, 0)),
        ],
    },
    {
        "username": "dr_karimi",
        "first_name": "رضا",
        "last_name": "کریمی",
        "email": "karimi@clinic.example",
        "phone": "09121110003",
        "specialty": "اطفال",
        "clinic_name": "کلینیک کودکان مهر",
        "clinic_address": "تهران، میدان ونک، خیابان گاندی، پلاک ۸",
        "latitude": "35.757500",
        "longitude": "51.410300",
        "visit_fee": "220000",
        "bio": "متخصص کودکان و نوزادان؛ پیگیری رشد، واکسیناسیون و بیماری‌های شایع کودکان.",
        "hours": [
            (5, time(16, 0), time(20, 0)),
            (0, time(9, 0), time(12, 0)),
            (2, time(16, 0), time(20, 0)),
        ],
    },
    {
        "username": "dr_rahimi",
        "first_name": "نگار",
        "last_name": "رحیمی",
        "email": "rahimi@clinic.example",
        "phone": "09121110004",
        "specialty": "مغز و اعصاب",
        "clinic_name": "کلینیک نور",
        "clinic_address": "تهران، خیابان شریعتی، نرسیده به میرداماد، پلاک ۲۱۰",
        "latitude": "35.761200",
        "longitude": "51.434700",
        "visit_fee": "400000",
        "bio": "متخصص مغز و اعصاب؛ سردرد، میگرن، صرع و اختلالات خواب.",
        "hours": [
            (6, time(9, 0), time(12, 0)),
            (1, time(9, 0), time(12, 0)),
            (2, time(17, 0), time(20, 0)),
        ],
    },
    {
        "username": "dr_hosseini",
        "first_name": "زهرا",
        "last_name": "حسینی",
        "email": "hosseini@clinic.example",
        "phone": "09121110005",
        "specialty": "زنان و زایمان",
        "clinic_name": "مطب دکتر حسینی",
        "clinic_address": "تهران، پاسداران، بوستان دوم، پلاک ۳۳",
        "latitude": "35.774100",
        "longitude": "51.457800",
        "visit_fee": "300000",
        "bio": "متخصص زنان و زایمان؛ مراقبت بارداری، سلامت بانوان و نازایی.",
        "hours": [
            (5, time(10, 0), time(13, 0)),
            (1, time(10, 0), time(13, 0)),
        ],
    },
]

PATIENTS = [
    {
        "username": "sara",
        "first_name": "سارا",
        "last_name": "محمدی",
        "email": "sara@example.com",
        "phone": "09121230001",
    },
    {
        "username": "reza",
        "first_name": "رضا",
        "last_name": "کاظمی",
        "email": "reza@example.com",
        "phone": "09121230002",
    },
    {
        "username": "maryam",
        "first_name": "مریم",
        "last_name": "نوری",
        "email": "maryam@example.com",
        "phone": "09121230003",
    },
    {
        "username": "amir",
        "first_name": "امیر",
        "last_name": "توکلی",
        "email": "amir@example.com",
        "phone": "09121230004",
    },
]

REVIEWS = [
    (5, "برخورد بسیار خوب و توضیحات کامل. حتماً دوباره مراجعه می‌کنم."),
    (4, "ویزیت منظم و دقیق بود؛ فقط کمی معطل شدم."),
    (5, "پزشک دلسوز و باتجربه‌ای هستند. سپاس."),
    (3, "درمان مؤثر بود اما زمان ویزیت کوتاه بود."),
]


def _last_date_with_weekday(weekday: int, weeks_ago: int):
    day = timezone.localdate() - timedelta(days=7 * weeks_ago)
    while day.weekday() != weekday:
        day -= timedelta(days=1)
    return day


class Command(BaseCommand):
    help = "ساخت داده‌های نمونه فارسی برای نمایش و آزمایش"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="حذف حساب‌ها و نوبت‌های نمونه و ساخت دوباره آن‌ها",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        doctor_usernames = [row["username"] for row in DOCTORS]
        patient_usernames = [row["username"] for row in PATIENTS]

        if options["reset"]:
            Appointment.objects.filter(
                patient__username__in=patient_usernames
            ).delete()
            Appointment.objects.filter(
                doctor__user__username__in=doctor_usernames
            ).delete()
            User.objects.filter(
                username__in=doctor_usernames + patient_usernames
            ).delete()
            self.stdout.write(self.style.WARNING("داده‌های نمونه قبلی حذف شد."))

        patients = [self._ensure_patient(row) for row in PATIENTS]
        doctors = [self._ensure_doctor(row) for row in DOCTORS]

        self._seed_future_bookings(doctors, patients)
        completed = self._seed_past_visits(doctors, patients)
        self._seed_cancelled(doctors, patients)
        self._seed_time_off(doctors)

        self.stdout.write(self.style.SUCCESS("داده‌های نمونه آماده است:"))
        self.stdout.write(
            f"  پزشکان: {DoctorProfile.objects.count()} | "
            f"بیماران نمونه: {len(patients)} | "
            f"ویزیت‌های تکمیل‌شده: {completed} | "
            f"نوبت‌های رزروشده آینده: "
            f"{Appointment.objects.filter(status=Appointment.Status.BOOKED).count()}"
        )
        self.stdout.write(
            "  ورود پزشکان: dr_ahmadi / dr_sadeghi / dr_karimi / "
            "dr_rahimi / dr_hosseini"
        )
        self.stdout.write("  ورود بیماران: sara / reza / maryam / amir")
        self.stdout.write(f"  گذرواژه همه حساب‌های نمونه: {DEMO_PASSWORD}")

    def _ensure_patient(self, row):
        user, _ = User.objects.get_or_create(
            username=row["username"],
            defaults={
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "email": row["email"],
                "phone": row["phone"],
                "role": User.Role.PATIENT,
            },
        )
        user.first_name = row["first_name"]
        user.last_name = row["last_name"]
        user.email = row["email"]
        user.phone = row["phone"]
        user.role = User.Role.PATIENT
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _ensure_doctor(self, row):
        user, _ = User.objects.get_or_create(
            username=row["username"],
            defaults={
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "email": row["email"],
                "phone": row["phone"],
                "role": User.Role.DOCTOR,
            },
        )
        user.first_name = row["first_name"]
        user.last_name = row["last_name"]
        user.email = row["email"]
        user.phone = row["phone"]
        user.role = User.Role.DOCTOR
        user.set_password(DEMO_PASSWORD)
        user.save()

        profile, _ = DoctorProfile.objects.get_or_create(
            user=user, defaults={"specialty": row["specialty"]}
        )
        profile.specialty = row["specialty"]
        profile.clinic_name = row["clinic_name"]
        profile.clinic_address = row["clinic_address"]
        profile.latitude = row["latitude"]
        profile.longitude = row["longitude"]
        profile.visit_fee = row["visit_fee"]
        profile.bio = row["bio"]
        profile.save()

        for weekday, start, end in row["hours"]:
            WorkingHours.objects.update_or_create(
                doctor=profile,
                weekday=weekday,
                start_time=start,
                defaults={"end_time": end},
            )
        return profile

    def _seed_future_bookings(self, doctors, patients):
        today = timezone.localdate()
        now_time = timezone.localtime().time()

        def pick(doctor, day, index):
            if doctor.time_off.filter(date=day).exists():
                return None
            slots = get_shift_slots(doctor, day)
            if day == today:
                slots = [slot for slot in slots if slot.start > now_time]
            if not slots:
                return None
            return slots[index % len(slots)]

        for offset in (1, 3, 6, 9):
            day = today + timedelta(days=offset)
            for index, doctor in enumerate(doctors):
                slot = pick(doctor, day, offset + index)
                if slot is None:
                    continue
                patient = patients[(offset + index) % len(patients)]
                Appointment.objects.get_or_create(
                    doctor=doctor,
                    date=day,
                    start_time=slot.start,
                    status=Appointment.Status.BOOKED,
                    defaults={
                        "patient": patient,
                        "end_time": slot.end,
                        "note": "ویزیت دوره‌ای" if offset % 2 else "مشاوره اولیه",
                    },
                )

        for index, doctor in enumerate(doctors):
            slot = pick(doctor, today, index)
            if slot is None:
                continue
            Appointment.objects.get_or_create(
                doctor=doctor,
                date=today,
                start_time=slot.start,
                status=Appointment.Status.BOOKED,
                defaults={
                    "patient": patients[index % len(patients)],
                    "end_time": slot.end,
                    "note": "مراجعه امروز",
                },
            )

    def _seed_past_visits(self, doctors, patients):
        count = 0
        for index, doctor in enumerate(doctors):
            shifts = list(doctor.working_hours.all())
            if not shifts:
                continue
            for step in range(2):
                shift = shifts[(index + step) % len(shifts)]
                day = _last_date_with_weekday(shift.weekday, weeks_ago=step + 1)
                start = (
                    datetime.combine(day, shift.start_time)
                    + timedelta(minutes=30 * (step + 1))
                ).time()
                end = (
                    datetime.combine(day, start) + timedelta(minutes=30)
                ).time()
                patient = patients[(index + step) % len(patients)]
                appointment, _ = Appointment.objects.get_or_create(
                    doctor=doctor,
                    date=day,
                    start_time=start,
                    defaults={
                        "patient": patient,
                        "end_time": end,
                        "status": Appointment.Status.COMPLETED,
                        "note": "ویزیت انجام‌شده",
                    },
                )
                if appointment.status != Appointment.Status.COMPLETED:
                    continue
                count += 1
                rating, comment = REVIEWS[(index + step) % len(REVIEWS)]
                Review.objects.get_or_create(
                    appointment=appointment,
                    defaults={"rating": rating, "comment": comment},
                )
        return count

    def _seed_cancelled(self, doctors, patients):
        day = timezone.localdate() + timedelta(days=2)
        for index, doctor in enumerate(doctors):
            slots = get_shift_slots(doctor, day)
            if not slots:
                continue
            slot = slots[-1]
            if Appointment.objects.filter(
                doctor=doctor, date=day, start_time=slot.start
            ).exists():
                continue
            Appointment.objects.create(
                doctor=doctor,
                date=day,
                start_time=slot.start,
                end_time=slot.end,
                status=Appointment.Status.CANCELLED,
                patient=patients[(index + 1) % len(patients)],
                note="لغو شده توسط بیمار",
            )

    def _seed_time_off(self, doctors):
        today = timezone.localdate()
        TimeOff.objects.update_or_create(
            doctor=doctors[0],
            date=today + timedelta(days=16),
            defaults={"reason": "مرخصی استعلاجی"},
        )
        TimeOff.objects.update_or_create(
            doctor=doctors[1],
            date=today + timedelta(days=18),
            defaults={"reason": "سفر کاری"},
        )
