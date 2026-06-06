"""Stay model — actual check-in/check-out lifecycle of a booking."""

from django.db import models


class Stay(models.Model):
    """A booking that has actually become a stay.

    Created automatically when a booking is checked-in. Holds the
    real-world data captured at the front desk.
    """

    booking = models.OneToOneField(
        "guesthouse.Booking",
        on_delete=models.CASCADE,
        related_name="stay",
    )
    actual_check_in = models.DateTimeField(db_index=True)
    actual_check_out = models.DateTimeField(null=True, blank=True, db_index=True)
    adults = models.PositiveSmallIntegerField(default=1)
    children = models.PositiveSmallIntegerField(default=0)
    vehicle_registration = models.CharField(max_length=40, blank=True)
    special_requests = models.TextField(blank=True)
    id_document_seen = models.BooleanField(default=False)
    key_card_no = models.CharField(max_length=40, blank=True)
    arrival_notes = models.TextField(blank=True)
    departure_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-actual_check_in",)

    @property
    def duration_nights(self):
        if self.actual_check_in and self.actual_check_out:
            delta = self.actual_check_out - self.actual_check_in
            return max(0, delta.days)
        return 0

    @property
    def is_open(self):
        return self.actual_check_out is None

    def __str__(self):
        return f"Stay for {self.booking.booking_reference}"
