from django.contrib import admin

from .models import Appointment, Review


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "start_time",
        "end_time",
        "patient",
        "doctor",
        "status",
        "created_at",
    )
    list_filter = ("status", "date", "doctor__specialty")
    search_fields = (
        "patient__username",
        "patient__email",
        "doctor__user__username",
    )
    date_hierarchy = "date"
    readonly_fields = ("created_at", "updated_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("appointment", "rating", "created_at")
    list_filter = ("rating",)
