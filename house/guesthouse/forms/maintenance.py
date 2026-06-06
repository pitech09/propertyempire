"""Room maintenance form."""

from django import forms

from guesthouse.models import Room, RoomMaintenance

from .rooms import BootstrapMixin


class RoomMaintenanceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = RoomMaintenance
        fields = [
            "room",
            "title",
            "issue",
            "priority",
            "status",
            "assigned_to",
            "resolution_notes",
            "cost",
        ]
        widgets = {
            "issue": forms.Textarea(attrs={"rows": 3}),
            "resolution_notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(active=True)
