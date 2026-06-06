"""Guest form."""

from django import forms

from guesthouse.models import Guest

from .rooms import BootstrapMixin


class GuestForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Guest
        fields = [
            "first_name",
            "last_name",
            "phone",
            "email",
            "national_id_or_passport",
            "nationality",
            "address",
            "notes",
            "is_vip",
            "marketing_opt_in",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
