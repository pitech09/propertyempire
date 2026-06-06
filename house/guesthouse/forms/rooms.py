"""Forms for RoomType & Room CRUD."""

from django import forms

from guesthouse.models import Room, RoomType


class BootstrapMixin:
    """Adds the `form-control` class to all widgets by default."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = (css + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (css + " form-select").strip()
            else:
                widget.attrs["class"] = (css + " form-control").strip()
            if not widget.attrs.get("placeholder"):
                widget.attrs["placeholder"] = field.label or name.title()


class RoomTypeForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = RoomType
        fields = [
            "name",
            "description",
            "default_capacity",
            "default_price",
            "icon",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class RoomForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Room
        fields = [
            "room_number",
            "room_name",
            "room_type",
            "description",
            "floor",
            "capacity",
            "status",
            "base_price_per_night",
            "weekend_price",
            "monthly_price_optional",
            "image",
            "amenities",
            "active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "amenities": forms.Textarea(attrs={"rows": 2}),
        }
