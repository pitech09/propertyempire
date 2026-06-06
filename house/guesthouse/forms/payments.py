"""Forms for guest payments."""

from django import forms

from guesthouse.models import Booking, GuestPayment

from .rooms import BootstrapMixin


class GuestPaymentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = GuestPayment
        fields = ["amount", "payment_method", "reference_number", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, booking: Booking | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking
        if booking and not self.initial.get("amount"):
            balance = booking.balance
            if balance > 0:
                self.initial["amount"] = balance
