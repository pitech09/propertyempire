"""Guest model — distinct from the long-term Tenant."""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Guest(models.Model):
    """Profile of a short-stay guest.

    A guest profile is intentionally reusable so that walk-in / online
    return customers don't have to re-register every time.
    """

    first_name = models.CharField(max_length=80, db_index=True)
    last_name = models.CharField(max_length=80, db_index=True)
    phone = models.CharField(max_length=32, db_index=True, blank=True)
    email = models.EmailField(blank=True, db_index=True)
    national_id_or_passport = models.CharField(max_length=64, blank=True, db_index=True)
    nationality = models.CharField(max_length=80, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    is_vip = models.BooleanField(default=False, db_index=True)
    marketing_opt_in = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_stay_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["phone"]),
        ]

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def clean(self):
        if not self.first_name or not self.last_name:
            raise ValidationError("Guest first and last name are required.")
        if not self.phone and not self.email:
            raise ValidationError(
                "At least one of phone or email must be provided for the guest."
            )

    def save(self, *args, **kwargs):
        # Normalize fields
        if self.phone:
            self.phone = self.phone.strip()
        if self.email:
            self.email = self.email.strip().lower()
        # Avoid full_clean during bulk imports / fixtures
        skip_validation = kwargs.pop("skip_validation", False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def total_stays(self):
        # Lazy import to break circular dependency
        from .booking import Booking

        return Booking.objects.filter(
            guest=self, booking_status=Booking.STATUS_CHECKED_OUT
        ).count()

    @property
    def total_spent(self):
        from django.db.models import Sum

        from .payment import GuestPayment

        total = GuestPayment.objects.filter(booking__guest=self).aggregate(
            total=Sum("amount")
        )["total"]
        return total or 0

    def touch_last_stay(self):
        self.last_stay_at = timezone.now()
        self.save(update_fields=["last_stay_at", "updated_at"])

    def __str__(self):
        return self.full_name
