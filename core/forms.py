from datetime import date, datetime

from django import forms

from .jalali import (
    format_jalali,
    jalali_to_gregorian,
    latin_digits,
    to_jalali,
)


class JalaliDateField(forms.DateField):
    """A text date field that accepts Jalali dates (۱۴۰۵/۰۹/۰۷)."""

    widget = forms.TextInput(
        attrs={
            "placeholder": "۱۴۰۵/۰۹/۰۷",
            "inputmode": "numeric",
            "dir": "ltr",
            "autocomplete": "off",
        }
    )

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, date):
            return value

        text = latin_digits(value).strip().replace("-", "/").replace(".", "/")
        parts = text.split("/")
        if (
            len(parts) == 3
            and all(part.isdigit() for part in parts)
            and 1200 <= int(parts[0]) <= 1600
        ):
            jy, jm, jd = (int(part) for part in parts)
            try:
                result = jalali_to_gregorian(jy, jm, jd)
            except ValueError:
                raise forms.ValidationError(
                    "تاریخ شمسی معتبر نیست.", code="invalid"
                )
            if to_jalali(result) != (jy, jm, jd):
                raise forms.ValidationError(
                    "تاریخ شمسی معتبر نیست.", code="invalid"
                )
            return result
        return super().to_python(value)

    def prepare_value(self, value):
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return format_jalali(value, "short")
        return super().prepare_value(value)
