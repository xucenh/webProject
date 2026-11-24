from django.contrib import admin
from django.urls import include, path

from core.views import home

admin.site.site_header = "مدیریت کلینیک مهر"
admin.site.site_title = "کلینیک مهر"
admin.site.index_title = "پنل مدیریت کلینیک"

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("doctors/", include("doctors.urls")),
    path("appointments/", include("appointments.urls")),
    path("doctor/", include("doctors.doctor_urls")),
]
