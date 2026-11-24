from django import forms
from django.utils import timezone

from core.forms import JalaliDateField

from .models import DoctorProfile, TimeOff, WorkingHours
from .services import WEEKDAY_CHOICES_FA


class DoctorSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="جستجو",
        widget=forms.TextInput(
            attrs={"placeholder": "نام پزشک، تخصص یا نام مطب…", "autocomplete": "off"}
        ),
    )


class DoctorProfileForm(forms.ModelForm):
    class Meta:
        model = DoctorProfile
        fields = (
            "specialty",
            "bio",
            "clinic_name",
            "clinic_address",
            "latitude",
            "longitude",
            "visit_fee",
        )
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 5}),
            "visit_fee": forms.NumberInput(attrs={"step": "1000", "min": "0"}),
            "latitude": forms.NumberInput(attrs={"step": "any"}),
            "longitude": forms.NumberInput(attrs={"step": "any"}),
        }
        labels = {
            "specialty": "تخصص",
            "bio": "درباره من",
            "clinic_name": "نام مطب یا کلینیک",
            "clinic_address": "نشانی مطب",
            "latitude": "عرض جغرافیایی",
            "longitude": "طول جغرافیایی",
            "visit_fee": "هزینه ویزیت (تومان)",
        }
        help_texts = {
            "latitude": "اختیاری؛ برای نمایش موقعیت روی نقشه.",
            "longitude": "اختیاری؛ برای نمایش موقعیت روی نقشه.",
        }


class WorkingHoursForm(forms.ModelForm):
    weekday = forms.TypedChoiceField(
        choices=WEEKDAY_CHOICES_FA,
        coerce=int,
        label="روز هفته",
    )

    class Meta:
        model = WorkingHours
        fields = ("weekday", "start_time", "end_time")
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
        }
        labels = {
            "start_time": "ساعت شروع",
            "end_time": "ساعت پایان",
        }

    def __init__(self, *args, doctor=None, **kwargs):
        self.doctor = doctor
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_time")
        end = cleaned.get("end_time")
        weekday = cleaned.get("weekday")
        if start and end and start >= end:
            raise forms.ValidationError("ساعت پایان باید بعد از ساعت شروع باشد.")
        if self.doctor and weekday is not None and start and end:
            overlaps = self.doctor.working_hours.filter(
                weekday=weekday,
                start_time__lt=end,
                end_time__gt=start,
            )
            if self.instance.pk:
                overlaps = overlaps.exclude(pk=self.instance.pk)
            if overlaps.exists():
                raise forms.ValidationError(
                    "این شیفت با یک شیفت دیگر در همان روز هم‌پوشانی دارد."
                )
        return cleaned


class TimeOffForm(forms.ModelForm):
    date = JalaliDateField(
        label="تاریخ",
        help_text="مثلاً ۱۴۰۵/۰۹/۰۷",
    )

    class Meta:
        model = TimeOff
        fields = ("date", "reason")
        widgets = {
            "reason": forms.TextInput(attrs={"placeholder": "مثلاً مرخصی استعلاجی"}),
        }
        labels = {
            "reason": "دلیل (اختیاری)",
        }

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day < timezone.localdate():
            raise forms.ValidationError("تاریخ مرخصی نمی‌تواند در گذشته باشد.")
        return day
