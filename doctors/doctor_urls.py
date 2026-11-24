from django.urls import path

from appointments import views as appointment_views

from . import views

app_name = "doctor"

urlpatterns = [
    path("profile/", views.doctor_profile, name="profile"),
    path("schedule/", views.doctor_schedule, name="schedule"),
    path(
        "schedule/hours/<int:pk>/edit/",
        views.doctor_hours_edit,
        name="hours_edit",
    ),
    path(
        "schedule/hours/<int:pk>/delete/",
        views.doctor_hours_delete,
        name="hours_delete",
    ),
    path(
        "schedule/timeoff/<int:pk>/delete/",
        views.doctor_timeoff_delete,
        name="timeoff_delete",
    ),
    path(
        "appointments/",
        appointment_views.doctor_appointments,
        name="appointments",
    ),
    path(
        "appointments/<int:pk>/complete/",
        appointment_views.complete_appointment,
        name="complete_appointment",
    ),
]
