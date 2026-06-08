"""Form for managing guest house property images."""

import os

from django import forms
from django.core.exceptions import ValidationError

from guesthouse.models import GuestHouseImage


class GuestHouseImageForm(forms.ModelForm):
    class Meta:
        model = GuestHouseImage
        fields = ["image", "caption", "sort_order"]
        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "caption": forms.TextInput(
                attrs={"placeholder": "e.g. Exterior, Lobby, Dining Area"}
            ),
            "sort_order": forms.NumberInput(attrs={"min": 0, "max": 100}),
        }
        help_texts = {
            "image": "Upload a photo (JPG, PNG, GIF, WebP). Max size: 5MB.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = field.widget.attrs.get("class", "")
            if isinstance(
                field.widget, (forms.CheckboxInput, forms.ClearableFileInput)
            ):
                field.widget.attrs["class"] = (css + " form-control").strip()
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs["class"] = (css + " form-select").strip()
            else:
                field.widget.attrs["class"] = (css + " form-control").strip()

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image:
            ext = os.path.splitext(image.name)[1].lower().lstrip(".")
            if ext not in GuestHouseImage.ALLOWED_EXTENSIONS:
                raise forms.ValidationError(
                    f"Image format not supported. "
                    f"Allowed: {', '.join(GuestHouseImage.ALLOWED_EXTENSIONS)}"
                )
            if image.size > GuestHouseImage.MAX_FILE_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(
                    f"Image must be less than {GuestHouseImage.MAX_FILE_SIZE_MB}MB."
                )
        return image

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk and GuestHouseImage.objects.count() >= GuestHouseImage.MAX_IMAGES:
            raise ValidationError(
                f"Maximum of {GuestHouseImage.MAX_IMAGES} images allowed. "
                "Please delete one before adding another."
            )
        return cleaned_data