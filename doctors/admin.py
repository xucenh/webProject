from django.contrib import admin

from .models import DoctorProfile, TimeOff, WorkingHours


class WorkingHoursInline(admin.TabularInline):
    model = WorkingHours
    extra = 1


class TimeOffInline(admin.TabularInline):
    model = TimeOff
    extra = 0


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialty", "clinic_name", "visit_fee", "average_rating")
    list_filter = ("specialty",)
    search_fields = ("user__username", "user__first_name", "user__last_name", "specialty")
    inlines = [WorkingHoursInline, TimeOffInline]
