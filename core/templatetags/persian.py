from django import template

from core.jalali import format_jalali, persian_digits, weekday_fa

register = template.Library()


@register.filter
def fa(value):
    return persian_digits(value)


@register.filter
def jdate(value):
    return format_jalali(value, "long")


@register.filter
def jdate_short(value):
    return format_jalali(value, "short")


@register.filter
def jdatetime(value):
    return format_jalali(value, "datetime")


@register.filter
def jdate_full(value):
    return format_jalali(value, "full")


@register.filter
def weekday(value):
    return weekday_fa(value)


@register.filter
def time_fa(value):
    if not value:
        return ""
    return persian_digits(value.strftime("%H:%M"))


@register.filter
def money_fa(value):
    if value in (None, ""):
        return persian_digits(0)
    return persian_digits(f"{int(value):,}")
