"""BookingService — high-level booking orchestration.

This is the entry point for everything booking-related that requires
multiple models / side effects (create, check-in, check-out, cancel,
record payment).
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils import timezone

from guesthouse.models import (
    Booking,
    Guest,
    GuestPayment,
    Room,
    Stay,
)
from guesthouse.services.availability import BookingAvailabilityService
from guesthouse.services.pricing import PricingService


class BookingError(Exception):
    """Raised when a booking operation is invalid."""


class BookingService:
    """Thin orchestration layer over the booking-related models."""

    # ------------------------------------------------------------------ #
    # Creation
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def create_booking(
        cls,
        *,
        guest: Guest,
        room: Room,
        check_in: _dt.date,
        check_out: _dt.date,
        adults: int = 1,
        children: int = 0,
        booking_source: str = Booking.SOURCE_WALK_IN,
        discount: Decimal | None = None,
        special_requests: str = "",
        internal_notes: str = "",
        by_user=None,
        tax_rate: Decimal | None = None,
        status: str = Booking.STATUS_CONFIRMED,
        skip_availability_check: bool = False,
    ) -> Booking:
        """Create a booking with full pricing + availability validation.

        Raises ``BookingError`` if the room isn't available or inputs are
        invalid.
        """
        if not skip_availability_check:
            conflicts = BookingAvailabilityService.detect_conflicts(
                room, check_in, check_out
            )
            if conflicts:
                detail = ", ".join(str(c) for c in conflicts)
                raise BookingError(
                    f"Room {room.room_number} is not available for the "
                    f"selected dates. {detail}"
                )

        booking = Booking(
            guest=guest,
            room=room,
            check_in_date=check_in,
            check_out_date=check_out,
            adults=adults,
            children=children,
            booking_source=booking_source,
            booking_status=status,
            discount=Decimal(discount or 0),
            special_requests=special_requests or "",
            internal_notes=internal_notes or "",
            created_by=by_user,
        )
        booking.full_clean()
        # Save first so we have a pk, then compute pricing (which needs the row)
        booking.save()
        PricingService.apply_to_booking(booking, tax_rate=tax_rate)
        booking.save(update_fields=[
            "nights", "room_rate", "subtotal", "taxes", "total_amount", "updated_at"
        ])
        return booking

    # ------------------------------------------------------------------ #
    # Reception flows
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def quick_check_in(
        cls, booking: Booking, *, by_user=None, vehicle_reg: str = "",
        special_requests: str = "", key_card_no: str = "", id_document_seen: bool = False,
    ) -> Stay:
        """Mark booking as checked-in and create the related Stay row."""
        if booking.booking_status == Booking.STATUS_CHECKED_OUT:
            raise BookingError("This booking has already been checked out.")
        booking.check_in(by_user=by_user)
        stay, _ = Stay.objects.update_or_create(
            booking=booking,
            defaults={
                "actual_check_in": booking.actual_check_in or timezone.now(),
                "actual_check_out": None,
                "adults": booking.adults,
                "children": booking.children,
                "vehicle_registration": vehicle_reg or "",
                "special_requests": special_requests or "",
                "key_card_no": key_card_no or "",
                "id_document_seen": id_document_seen,
            },
        )
        return stay

    @classmethod
    @transaction.atomic
    def quick_check_out(
        cls,
        booking: Booking,
        *,
        by_user=None,
        extra_charges: Decimal | None = None,
        departure_notes: str = "",
    ) -> Booking:
        if booking.booking_status not in (
            Booking.STATUS_CHECKED_IN,
            Booking.STATUS_CONFIRMED,
        ):
            raise BookingError(
                f"Cannot check-out a booking with status "
                f"{booking.get_booking_status_display()}."
            )
        booking.check_out(by_user=by_user, extra_charges=extra_charges)
        if hasattr(booking, "stay"):
            stay = booking.stay
            stay.actual_check_out = booking.actual_check_out
            if departure_notes:
                stay.departure_notes = departure_notes
            stay.save()
        return booking

    # ------------------------------------------------------------------ #
    # Walk-in flow (create guest + booking + payment in one go)
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def walk_in_booking(
        cls,
        *,
        first_name: str,
        last_name: str,
        phone: str = "",
        email: str = "",
        national_id: str = "",
        room: Room,
        check_in: _dt.date,
        check_out: _dt.date,
        adults: int = 1,
        children: int = 0,
        payment_method: str = GuestPayment.METHOD_CASH,
        payment_amount: Decimal | None = None,
        payment_reference: str = "",
        special_requests: str = "",
        by_user=None,
    ) -> tuple[Booking, GuestPayment]:
        guest, _ = Guest.objects.get_or_create(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone.strip() or Guest._default_manager.none().first() and "" or "",
            defaults={
                "email": email.strip().lower(),
                "national_id_or_passport": national_id.strip(),
            },
        )
        # If the guest already exists by phone we may want to update contact
        # info; the get_or_create is the simplest robust path.
        booking = cls.create_booking(
            guest=guest,
            room=room,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            booking_source=Booking.SOURCE_WALK_IN,
            special_requests=special_requests,
            by_user=by_user,
            status=Booking.STATUS_CONFIRMED,
        )
        # Auto check-in for walk-ins (the guest is at the desk)
        cls.quick_check_in(
            booking, by_user=by_user, special_requests=special_requests
        )
        # Record the first payment (if any)
        if payment_amount and Decimal(payment_amount) > 0:
            payment = GuestPayment.objects.create(
                booking=booking,
                amount=Decimal(payment_amount),
                payment_method=payment_method,
                reference_number=payment_reference or "",
                received_by=by_user,
            )
        else:
            payment = None
        return booking, payment

    # ------------------------------------------------------------------ #
    # Cancellations
    # ------------------------------------------------------------------ #
    @classmethod
    @transaction.atomic
    def cancel_booking(
        cls, booking: Booking, *, reason: str = "", by_user=None
    ) -> Booking:
        if booking.booking_status == Booking.STATUS_CHECKED_IN:
            raise BookingError(
                "Cannot cancel a checked-in booking. Please check the guest out first."
            )
        booking.cancel(reason=reason, by_user=by_user)
        return booking

    # ------------------------------------------------------------------ #
    # Record payment helper
    # ------------------------------------------------------------------ #
    @classmethod
    def record_payment(
        cls,
        booking: Booking,
        amount: Decimal,
        payment_method: str = GuestPayment.METHOD_CASH,
        reference_number: str = "",
        notes: str = "",
        by_user=None,
    ) -> GuestPayment:
        payment = GuestPayment.objects.create(
            booking=booking,
            amount=Decimal(amount),
            payment_method=payment_method,
            reference_number=reference_number or "",
            notes=notes or "",
            received_by=by_user,
        )
        return payment
