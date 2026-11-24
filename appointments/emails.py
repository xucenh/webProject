import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

from core.jalali import format_jalali, persian_digits

logger = logging.getLogger(__name__)


def _send(subject: str, body: str, recipients: list[str]) -> None:
    recipients = [email for email in recipients if email]
    if not recipients:
        return
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception:
        # FR-17: mail is a notification, not part of the booking transaction.
        logger.exception("Sending clinic email failed: %s", subject)


def _when(appointment) -> str:
    return (
        f"{format_jalali(appointment.date, 'full')} "
        f"ساعت {persian_digits(appointment.start_time.strftime('%H:%M'))}"
    )


def send_booking_confirmation(request, appointment) -> None:
    doctor = appointment.doctor
    patient = appointment.patient
    doctor_link = request.build_absolute_uri(
        reverse("doctors:detail", args=[doctor.pk])
    )
    _send(
        "نوبت شما با موفقیت ثبت شد",
        (
            f"{patient.get_full_name() or patient.username} عزیز،\n\n"
            f"نوبت شما با دکتر {doctor.user.get_full_name() or doctor.user.username} "
            f"({doctor.specialty}) در {_when(appointment)} ثبت شد.\n"
            f"نشانی مطب: {doctor.clinic_address or '—'}\n"
            f"صفحه پزشک: {doctor_link}\n\n"
            "در صورت نیاز می‌توانید از بخش «نوبت‌های من» نوبت را لغو کنید.\n"
            "کلینیک مهر"
        ),
        [patient.email],
    )
    _send(
        "نوبت جدید برای شما ثبت شد",
        (
            f"دکتر {doctor.user.get_full_name() or doctor.user.username} عزیز،\n\n"
            f"بیمار {patient.get_full_name() or patient.username} "
            f"برای {_when(appointment)} نوبت گرفت.\n"
            f"شماره تماس بیمار: {patient.phone or '—'}\n"
            f"توضیح بیمار: {appointment.note or '—'}\n\n"
            "کلینیک مهر"
        ),
        [doctor.user.email],
    )


def send_cancellation_notice(appointment) -> None:
    doctor = appointment.doctor
    patient = appointment.patient
    _send(
        "لغو نوبت توسط بیمار",
        (
            f"دکتر {doctor.user.get_full_name() or doctor.user.username} عزیز،\n\n"
            f"بیمار {patient.get_full_name() or patient.username} "
            f"نوبت {_when(appointment)} را لغو کرد.\n"
            "این زمان دوباره برای بیماران دیگر آزاد شد.\n\n"
            "کلینیک مهر"
        ),
        [doctor.user.email],
    )


def send_review_invitation(request, appointment) -> None:
    patient = appointment.patient
    doctor = appointment.doctor
    link = request.build_absolute_uri(
        reverse("appointments:review", args=[appointment.pk])
    )
    _send(
        "ویزیت شما تکمیل شد؛ نظرتان را ثبت کنید",
        (
            f"{patient.get_full_name() or patient.username} عزیز،\n\n"
            f"ویزیت شما با دکتر {doctor.user.get_full_name() or doctor.user.username} "
            f"در {_when(appointment)} تکمیل شد.\n"
            f"برای ثبت امتیاز و نظر از این پیوند استفاده کنید:\n{link}\n\n"
            "نظر شما به انتخاب پزشک توسط بیماران دیگر کمک می‌کند.\n"
            "کلینیک مهر"
        ),
        [patient.email],
    )


def send_reminder(appointment) -> None:
    patient = appointment.patient
    doctor = appointment.doctor
    _send(
        "یادآوری نوبت فردا",
        (
            f"{patient.get_full_name() or patient.username} عزیز،\n\n"
            f"یادآوری می‌کنیم نوبت شما با دکتر "
            f"{doctor.user.get_full_name() or doctor.user.username} "
            f"در {_when(appointment)} است.\n"
            f"نشانی مطب: {doctor.clinic_address or '—'}\n\n"
            "کلینیک مهر"
        ),
        [patient.email],
    )
