"""Housekeeping task form."""

from django import forms

from guesthouse.models import HousekeepingTask, Room

from .rooms import BootstrapMixin


class HousekeepingTaskForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = HousekeepingTask
        fields = [
            "room",
            "assigned_to",
            "task_type",
            "priority",
            "status",
            "scheduled_date",
            "notes",
        ]
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["room"].queryset = Room.objects.filter(active=True)
        self.fields["scheduled_date"].input_formats = ["%Y-%m-%d"]
