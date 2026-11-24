from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render

from core.utils import role_landing

from .forms import ClinicAuthenticationForm, SignupForm


def signup(request):
    if request.user.is_authenticated:
        return redirect(role_landing(request.user))

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user)
        messages.success(request, "حساب شما ساخته شد. خوش آمدید!")
        return redirect(role_landing(user))

    return render(request, "accounts/signup.html", {"form": form})


class ClinicLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = ClinicAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or role_landing(self.request.user)
