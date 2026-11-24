from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from doctors.models import DoctorProfile

from .models import User


class ClinicAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
    )
    password = forms.CharField(
        label="گذرواژه",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=(("patient", "بیمار"), ("doctor", "پزشک")),
        initial="patient",
        widget=forms.RadioSelect,
        label="نقش",
    )
    specialty = forms.CharField(
        required=False,
        max_length=100,
        label="تخصص",
        widget=forms.TextInput(attrs={"placeholder": "مثلاً قلب و عروق"}),
    )
    clinic_name = forms.CharField(
        required=False,
        max_length=120,
        label="نام مطب یا کلینیک",
    )
    clinic_address = forms.CharField(
        required=False,
        max_length=255,
        label="نشانی مطب",
    )
    visit_fee = forms.DecimalField(
        required=False,
        min_value=0,
        initial=0,
        label="هزینه ویزیت (تومان)",
        widget=forms.NumberInput(attrs={"step": "1000"}),
    )
    bio = forms.CharField(
        required=False,
        label="درباره من",
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    field_order = [
        "role",
        "first_name",
        "last_name",
        "username",
        "email",
        "phone",
        "password1",
        "password2",
        "specialty",
        "clinic_name",
        "clinic_address",
        "visit_fee",
        "bio",
    ]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "username": "نام کاربری",
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "email": "ایمیل",
            "phone": "شماره تماس",
        }
        for name, label in labels.items():
            self.fields[name].label = label

        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].required = True
        self.fields["username"].help_text = "فقط حروف انگلیسی، عدد و @/./+/-/_"
        self.fields["username"].widget.attrs["placeholder"] = "مثلاً ali_ahmadi"
        self.fields["email"].widget.attrs["placeholder"] = "you@example.com"
        self.fields["phone"].widget.attrs["placeholder"] = "09121234567"
        self.fields["phone"].help_text = "برای هماهنگی نوبت استفاده می‌شود."
        self.fields["first_name"].widget.attrs["placeholder"] = "نام"
        self.fields["last_name"].widget.attrs["placeholder"] = "نام خانوادگی"
        self.fields["password1"].label = "گذرواژه"
        self.fields["password2"].label = "تکرار گذرواژه"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("role") == User.Role.DOCTOR:
            if not cleaned.get("specialty"):
                self.add_error("specialty", "برای حساب پزشک، تخصص الزامی است.")
            if not cleaned.get("clinic_name"):
                self.add_error("clinic_name", "نام مطب یا کلینیک را وارد کنید.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and user.role == User.Role.DOCTOR:
            DoctorProfile.objects.create(
                user=user,
                specialty=self.cleaned_data["specialty"],
                clinic_name=self.cleaned_data["clinic_name"],
                clinic_address=self.cleaned_data["clinic_address"],
                visit_fee=self.cleaned_data["visit_fee"] or 0,
                bio=self.cleaned_data["bio"],
            )
        return user
