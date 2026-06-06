"""Guest payments — separate ledger from long-term tenant payments."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class GuestPayment(models.Model):
    """A payment made by a guest towards a booking."""

    METHOD_CASH = "cash"
    METHOD_CARD = "card"
    METHOD_EFT = "eft"
    METHOD_MOBILE_MONEY = "mobile_money"
    METHOD_OTHER = "other"

    METHOD_CHOICES = (
        (METHOD_CASH, "Cash"),
        (METHOD_CARD, "Card"),
        (METHOD_EFT, "EFT"),
        (METHOD_MOBILE_MONEY, "Mobile Money"),
        (METHOD_OTHER, "Other"),
    )

    booking = models.ForeignKey(
        "guesthouse.Booking",
        on_delete=models.CASCADE,
        related_name="payments",
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, db_index=True
    )
    payment_method = models.CharField(
        max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH, db_index=True
    )
    payment_date = models.DateTimeField(default=timezone.now, db_index=True)
    reference_number = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guest_payments_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-payment_date", "-created_at")
        indexes = [
            models.Index(fields=["payment_method", "payment_date"]),
        ]

    def clean(self):
        if self.amount is None or self.amount <= Decimal("0"):
            raise ValidationError({"amount": "Payment amount must be greater than zero."})
        if self.payment_method != self.METHOD_CASH and not self.reference_number:
            raise ValidationError(
                {"reference_number": "Reference number is required for non-cash payments."}
            )

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.booking_id:
            # Roll the amount into the booking's cached amount_paid
            from django.db.models import F, Sum
            from django.db.models.functions import Coalesce

            agg = self.booking.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
            type(self.booking).objects.filter(pk=self.booking_id).update(
                amount_paid=agg, updated_at=timezone.now()
            )

    def __str__(self):
        return f"{self.amount} - {self.booking.booking_reference} via {self.get_payment_method_display()}"
