"""Forms for RoomType & Room CRUD."""

import os

from django import forms

from guesthouse.models import Room, RoomImage, RoomType


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


# ------------------------------
# Room Image Form (up to 5 pictures per room)
# ------------------------------
class RoomImageForm(forms.ModelForm):
    class Meta:
        model = RoomImage
        fields = ["image", "caption", "sort_order"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "caption": forms.TextInput(attrs={"placeholder": "Optional caption (e.g. Bathroom, Balcony)"}),
            "sort_order": forms.NumberInput(attrs={"min": 0, "max": 100}),
        }
        help_texts = {
            "image": "Upload a photo (JPG, PNG, GIF, WebP). Max size: 5MB.",
        }

    def __init__(self, room=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            ext = os.path.splitext(image.name)[1].lower().lstrip(".")
            if ext not in RoomImage.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f"Image format not supported. Allowed: {', '.join(RoomImage.ALLOWED_EXTENSIONS)}"
                )
            if image.size > RoomImage.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(f"Image must be less than {RoomImage.MAX_FILE_SIZE_MB}MB.")
        return image

    def clean(self):
        cleaned_data = super().clean()
        if self.room:
            from django.core.exceptions import ValidationError as VE
            existing = self.room.images.count()
            if existing >= RoomImage.MAX_IMAGES:
                raise VE(
                    f"Maximum of {RoomImage.MAX_IMAGES} images allowed. "
                    "Please delete one before adding another."
                )
        return cleaned_data
