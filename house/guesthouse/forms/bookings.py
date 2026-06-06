"""Booking forms — including the walk-in flow."""

from datetime import date

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from guesthouse.models import Booking, Guest, Room
from guesthouse.services.availability import BookingAvailabilityService

from .rooms import BootstrapMixin


class BookingForm(BootstrapMixin, forms.ModelForm):
    """Used by the standard reservation form."""

    class Meta:
        model = Booking
        fields = [
            "guest",
            "room",
            "booking_source",
            "booking_status",
            "check_in_date",
            "check_out_date",
            "adults",
            "children",
            "discount",
            "special_requests",
            "internal_notes",
        ]
        widgets = {
            "check_in_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "check_out_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "special_requests": forms.Textarea(attrs={"rows": 2}),
            "internal_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ("check_in_date", "check_out_date"):
            self.fields[f].input_formats = ["%Y-%m-%d"]
        # Restrict room queryset to active rooms
        self.fields["room"].queryset = Room.objects.filter(active=True)
        if not self.instance.pk and not self.initial.get("check_in_date"):
            self.initial["check_in_date"] = timezone.localdate()
            self.initial["check_out_date"] = (
                timezone.localdate() + timezone.timedelta(days=1)
            )

    def clean(self):
        cleaned = super().clean()
        ci = cleaned.get("check_in_date")
        co = cleaned.get("check_out_date")
        room = cleaned.get("room")
        if ci and co and co <= ci:
            raise ValidationError(
                {"check_out_date": "Check-out must be after check-in."}
            )
        if room and ci and co:
            conflicts = BookingAvailabilityService.detect_conflicts(
                room,
                ci,
                co,
                exclude_booking_id=self.instance.pk or None,
            )
            if conflicts:
                raise ValidationError(
                    "Room is already booked for the selected dates: "
                    + ", ".join(c.booking.booking_reference for c in conflicts)
                )
        return cleaned


class WalkInBookingForm(BootstrapMixin, forms.Form):
    """One-shot walk-in: create guest + booking + optional payment."""

    # Guest fields
    first_name = forms.CharField(max_length=80)
    last_name = forms.CharField(max_length=80)
    phone = forms.CharField(max_length=32, required=False)
    email = forms.EmailField(required=False)
    national_id = forms.CharField(max_length=64, required=False)

    # Booking fields
    room = forms.ModelChoiceField(queryset=Room.objects.filter(active=True))
    check_in_date = forms.DateField(
        initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"})
    )
    check_out_date = forms.DateField(
        initial=lambda: timezone.localdate() + timezone.timedelta(days=1),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    adults = forms.IntegerField(min_value=1, initial=1)
    children = forms.IntegerField(min_value=0, initial=0)
    special_requests = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2})
    )

    # Payment fields
    payment_amount = forms.DecimalField(
        min_value=0,
        required=False,
        initial=0,
        help_text="Optional initial payment to record.",
    )
    payment_method = forms.ChoiceField(
        choices=Booking._meta.get_field("booking_source").choices if False else [
            ("cash", "Cash"),
            ("card", "Card"),
            ("eft", "EFT"),
            ("mobile_money", "Mobile Money"),
            ("other", "Other"),
        ],
        initial="cash",
    )
    payment_reference = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["check_in_date"].input_formats = ["%Y-%m-%d"]
        self.fields["check_out_date"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned = super().clean()
        ci = cleaned.get("check_in_date")
        co = cleaned.get("check_out_date")
        if ci and co and co <= ci:
            raise ValidationError(
                {"check_out_date": "Check-out must be after check-in."}
            )
        room = cleaned.get("room")
        if room and ci and co:
            conflicts = BookingAvailabilityService.detect_conflicts(room, ci, co)
            if conflicts:
                raise ValidationError(
                    "Room is already booked for the selected dates."
                )
        return cleaned
