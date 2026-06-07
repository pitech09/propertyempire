from __future__ import annotations

from django import forms

from marketplace.models import PropertyInquiry, PropertyReview


class TailwindMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            base = "block w-full rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-slate-900 shadow-sm outline-none transition focus:border-slate-400 focus:ring-4 focus:ring-slate-200"
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = (css + " h-4 w-4 rounded border-slate-300 text-slate-900").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (css + " " + base).strip()
            else:
                widget.attrs["class"] = (css + " " + base).strip()
            if not widget.attrs.get("placeholder") and field.label:
                widget.attrs["placeholder"] = field.label


class MarketplaceSearchForm(TailwindMixin, forms.Form):
    location = forms.CharField(required=False, label="Location")
    check_in = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    check_out = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    guests = forms.IntegerField(required=False, min_value=1, initial=2)
    property_type = forms.CharField(required=False)
    price_min = forms.DecimalField(required=False, min_value=0)
    price_max = forms.DecimalField(required=False, min_value=0)
    bedrooms = forms.IntegerField(required=False, min_value=0)
    bathrooms = forms.IntegerField(required=False, min_value=0)
    wifi = forms.BooleanField(required=False)
    parking = forms.BooleanField(required=False)
    swimming_pool = forms.BooleanField(required=False)
    air_conditioning = forms.BooleanField(required=False)


class PublicLeadForm(TailwindMixin, forms.Form):
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    phone = forms.CharField(max_length=40, required=False)
    check_in = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    check_out = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    guests = forms.IntegerField(required=False, min_value=1, initial=1)
    message = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def clean(self):
        cleaned = super().clean()
        ci = cleaned.get("check_in")
        co = cleaned.get("check_out")
        if ci and co and co <= ci:
            raise forms.ValidationError({"check_out": "Check-out must be after check-in."})
        return cleaned


class PropertyReviewForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = PropertyReview
        fields = ["reviewer_name", "reviewer_email", "rating", "title", "body"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 1, "max": 5}),
            "body": forms.Textarea(attrs={"rows": 4}),
        }


class PropertyInquiryModelForm(TailwindMixin, forms.ModelForm):
    class Meta:
        model = PropertyInquiry
        fields = ["full_name", "email", "phone", "check_in", "check_out", "guests", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
            "check_in": forms.DateInput(attrs={"type": "date"}),
            "check_out": forms.DateInput(attrs={"type": "date"}),
        }
