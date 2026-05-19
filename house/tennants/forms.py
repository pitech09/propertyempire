from django import forms
from .models import House, Payment, Tenant, FlatBuilding, LandlordProfile, RentCharge, PaymentRequest
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from phonenumber_field.formfields import PhoneNumberField



class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(required=True, max_length=30)
    last_name = forms.CharField(required=True, max_length=30)
    email = forms.EmailField(required=True)
    phone = PhoneNumberField(required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "phone", "password1", "password2"]

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if LandlordProfile.objects.filter(phone=phone).exists():
            raise forms.ValidationError("A landlord with this phone number already exists.")
        return phone


class SMSPasswordResetRequestForm(forms.Form):
    identifier = forms.CharField(
        label="Username, email, or phone",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username, email, or phone"}),
    )


class SMSPasswordResetConfirmForm(forms.Form):
    code = forms.CharField(
        label="Reset code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "6-digit code"}),
    )
    new_password = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "New password"}),
    )
    confirm_password = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("new_password") != cleaned_data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data


class HouseForm(forms.ModelForm):
    class Meta:
        model = House
        fields = '__all__'

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = '__all__'

class FlatBuildingForm(forms.ModelForm):
    class Meta:
        model = FlatBuilding
        fields = '__all__'

class RentChargeForm(forms.ModelForm):
    class Meta:
        model = RentCharge
        fields = '__all__'

class PaymentInitForm(forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields ='__all__'


# Additional forms can be added here as needed
