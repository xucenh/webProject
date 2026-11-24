"""Gregorian → Jalali conversion and Persian display helpers.

Django ships a Persian locale, but Python's ``strftime`` has no Jalali
calendar.  These helpers keep every date shown in the UI in the Iranian
calendar without adding a third-party dependency.
"""

from datetime import date, datetime

from django.utils import timezone

MONTHS_FA = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

# Python's ``date.weekday()``: Monday == 0.
WEEKDAYS_FA = (
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنج‌شنبه",
    "جمعه",
    "شنبه",
    "یکشنبه",
)

_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_LATIN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)


def persian_digits(value) -> str:
    """Convert Latin digits in *value* to Persian digits."""
    if value is None:
        return ""
    return str(value).translate(_DIGITS)


def latin_digits(value) -> str:
    """Convert Persian/Arabic-Indic digits in *value* to Latin digits."""
    if value is None:
        return ""
    return str(value).translate(_LATIN_DIGITS)


def to_jalali(value: date) -> tuple[int, int, int]:
    """Return the Jalali ``(year, month, day)`` for a Gregorian date."""
    gy, gm, gd = value.year, value.month, value.day
    month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    day_no = (
        365 * gy2
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        + month_days[gm2]
        + gd2
    )
    if gm > 2 and (gy % 4 == 0 and gy % 100 != 0 or gy % 400 == 0):
        day_no += 1

    j_day_no = day_no - 79
    cycle, j_day_no = divmod(j_day_no, 12053)
    jy = 979 + 33 * cycle + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def is_leap_jalali(year: int) -> bool:
    return year % 33 in {1, 5, 9, 13, 17, 22, 26, 30}


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    """Return the Gregorian date for a Jalali ``(year, month, day)``."""
    days_in_month = (
        31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30,
        30 if is_leap_jalali(jy) else 29,
    )
    if jm < 1 or jm > 12 or jd < 1 or jd > days_in_month[jm - 1]:
        raise ValueError("تاریخ شمسی معتبر نیست.")

    jy += 1595
    days = (
        -355668
        + 365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365

    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    month_days = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 1
    for days_in_month in month_days:
        if gd <= days_in_month:
            break
        gd -= days_in_month
        gm += 1
    return date(gy, gm, gd)


def _local_date(value) -> date:
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date()
    return value


def format_jalali(value, style: str = "long") -> str:
    """Format a date/datetime in Persian.

    Styles: ``short`` (۱۴۰۵/۰۹/۰۲), ``long`` (۲ آذر ۱۴۰۵),
    ``full`` (دوشنبه ۲ آذر ۱۴۰۵) and ``datetime`` (long + time).
    """
    if not value:
        return ""
    day = _local_date(value)
    jy, jm, jd = to_jalali(day)

    if style == "short":
        return persian_digits(f"{jy:04d}/{jm:02d}/{jd:02d}")

    label = f"{persian_digits(jd)} {MONTHS_FA[jm - 1]} {persian_digits(jy)}"
    if style == "full":
        label = f"{WEEKDAYS_FA[day.weekday()]} {label}"
    if style == "datetime" and isinstance(value, datetime):
        local = timezone.localtime(value) if timezone.is_aware(value) else value
        label = f"{label}، ساعت {persian_digits(local.strftime('%H:%M'))}"
    return label


def weekday_fa(value) -> str:
    """Persian weekday name for a date or a ``weekday()`` integer."""
    if isinstance(value, int):
        return WEEKDAYS_FA[value]
    return WEEKDAYS_FA[_local_date(value).weekday()]
