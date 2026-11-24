from django import forms
from django.utils import timezone

from core.forms import JalaliDateField

from .models import Review

RATING_CHOICES = (
    (5, "عالی"),
    (4, "خوب"),
    (3, "متوسط"),
    (2, "ضعیف"),
    (1, "خیلی ضعیف"),
)


class BookingForm(forms.Form):
    date = JalaliDateField(
        label="تاریخ",
        help_text="مثلاً ۱۴۰۵/۰۹/۰۷",
    )
    start_time = forms.TimeField(
        label="ساعت",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    note = forms.CharField(
        required=False,
        label="توضیح برای پزشک (اختیاری)",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "مثلاً درد قفسه سینه از دو روز پیش…",
            }
        ),
    )

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day < timezone.localdate():
            raise forms.ValidationError("رزرو نوبت برای تاریخ گذشته ممکن نیست.")
        return day


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        label="امتیاز شما",
    )

    class Meta:
        model = Review
        fields = ("rating", "comment")
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "تجربه خود از این ویزیت را بنویسید (اختیاری)",
                }
            )
        }
        labels = {"comment": "نظر شما (اختیاری)"}
