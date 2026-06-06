"""Booking model — a reservation of a Room for a Guest."""

import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


def _generate_booking_reference() -> str:
    """Create a short, human-friendly booking reference."""
    return f"BK-{timezone.now().strftime('%y%m%d')}-{secrets.token_hex(3).upper()}"


class Booking(models.Model):
    """A room reservation made by a Guest."""

    # ----- Status choices ----- #
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CHECKED_IN = "checked_in"
    STATUS_CHECKED_OUT = "checked_out"
    STATUS_CANCELLED = "cancelled"
    STATUS_NO_SHOW = "no_show"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CHECKED_IN, "Checked In"),
        (STATUS_CHECKED_OUT, "Checked Out"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_NO_SHOW, "No Show"),
    )

    # ----- Source choices ----- #
    SOURCE_WALK_IN = "walk_in"
    SOURCE_PHONE = "phone"
    SOURCE_WEBSITE = "website"
    SOURCE_BOOKING_COM = "booking_com"
    SOURCE_AIRBNB = "airbnb"
    SOURCE_AGENT = "agent"
    SOURCE_OTHER = "other"

    SOURCE_CHOICES = (
        (SOURCE_WALK_IN, "Walk In"),
        (SOURCE_PHONE, "Phone"),
        (SOURCE_WEBSITE, "Website"),
        (SOURCE_BOOKING_COM, "Booking.com"),
        (SOURCE_AIRBNB, "Airbnb"),
        (SOURCE_AGENT, "Agent"),
        (SOURCE_OTHER, "Other"),
    )

    # ----- Core fields ----- #
    booking_reference = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        default=_generate_booking_reference,
    )
    guest = models.ForeignKey(
        "guesthouse.Guest",
        on_delete=models.PROTECT,
        related_name="bookings",
        db_index=True,
    )
    room = models.ForeignKey(
        "guesthouse.Room",
        on_delete=models.PROTECT,
        related_name="bookings",
        db_index=True,
    )
    booking_source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_WALK_IN, db_index=True
    )
    booking_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )

    # ----- Dates ----- #
    booking_date = models.DateTimeField(default=timezone.now, db_index=True)
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    actual_check_in = models.DateTimeField(null=True, blank=True)
    actual_check_out = models.DateTimeField(null=True, blank=True)

    # ----- Guests & stay details ----- #
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)

    # ----- Pricing (snapshotted at booking time) ----- #
    nights = models.PositiveIntegerField(default=1)
    room_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extra_charges = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Any extra charges (minibar, damages, late checkout) added at checkout.",
    )
    amount_paid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, db_index=True
    )

    special_requests = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # ----- Audit ----- #
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings_created",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-check_in_date", "-created_at")
        indexes = [
            models.Index(fields=["check_in_date", "check_out_date"]),
            models.Index(fields=["booking_status", "check_in_date"]),
        ]

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def clean(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValidationError(
                    {"check_out_date": "Check-out date must be after check-in date."}
                )
        if self.adults < 1:
            raise ValidationError({"adults": "At least one adult guest is required."})
        if self.children < 0:
            raise ValidationError({"children": "Children count cannot be negative."})
        if self.room_id and self.adults + self.children > self.room.capacity:
            raise ValidationError(
                {
                    "adults": (
                        f"This room sleeps a maximum of {self.room.capacity} guests. "
                        f"You selected {self.adults + self.children}."
                    )
                }
            )

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #
    def save(self, *args, **kwargs):
        # Compute nights
        if self.check_in_date and self.check_out_date:
            self.nights = max(
                1, (self.check_out_date - self.check_in_date).days
            )
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------ #
    # Convenience properties
    # ------------------------------------------------------------------ #
    @property
    def balance(self):
        """Outstanding balance for the booking."""
        return (self.total_amount or 0) + (self.extra_charges or 0) - (self.amount_paid or 0)

    @property
    def is_active(self):
        return self.booking_status in (
            self.STATUS_PENDING,
            self.STATUS_CONFIRMED,
            self.STATUS_CHECKED_IN,
        )

    @property
    def status_badge_class(self):
        return {
            self.STATUS_PENDING: "badge-warning",
            self.STATUS_CONFIRMED: "badge-info",
            self.STATUS_CHECKED_IN: "badge-success",
            self.STATUS_CHECKED_OUT: "badge-secondary",
            self.STATUS_CANCELLED: "badge-danger",
            self.STATUS_NO_SHOW: "badge-danger",
        }.get(self.booking_status, "badge-info")

    def __str__(self):
        return f"{self.booking_reference} - {self.guest.full_name} - Room {self.room.room_number}"

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    @transaction.atomic
    def confirm(self, by_user=None):
        self.booking_status = self.STATUS_CONFIRMED
        self.save(update_fields=["booking_status", "updated_at"])

    @transaction.atomic
    def check_in(self, by_user=None, actual_time=None):
        self.booking_status = self.STATUS_CHECKED_IN
        self.actual_check_in = actual_time or timezone.now()
        # Update room status
        if self.room_id:
            self.room.status = self.room.STATUS_OCCUPIED
            self.room.save(update_fields=["status", "updated_at"])
        self.save(update_fields=["booking_status", "actual_check_in", "updated_at"])

    @transaction.atomic
    def check_out(self, by_user=None, actual_time=None, extra_charges=None):
        self.booking_status = self.STATUS_CHECKED_OUT
        self.actual_check_out = actual_time or timezone.now()
        if extra_charges is not None:
            self.extra_charges = extra_charges
        if self.room_id:
            # After checkout the room moves to cleaning before being available again
            self.room.status = self.room.STATUS_CLEANING
            self.room.save(update_fields=["status", "updated_at"])
        self.save(
            update_fields=[
                "booking_status",
                "actual_check_out",
                "extra_charges",
                "updated_at",
            ]
        )
        # Mark guest's last stay
        if self.guest_id:
            self.guest.touch_last_stay()

    @transaction.atomic
    def cancel(self, reason: str = "", by_user=None):
        self.booking_status = self.STATUS_CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason or ""
        self.save(
            update_fields=[
                "booking_status",
                "cancelled_at",
                "cancellation_reason",
                "updated_at",
            ]
        )
