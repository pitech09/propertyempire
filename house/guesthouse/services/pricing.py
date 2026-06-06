"""PricingService — calculates stay pricing consistently.

All pricing math is centralised here so the same rules apply when
booking via the web form, the walk-in flow, the calendar or the API.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List

from guesthouse.models import Room


@dataclass
class NightlyRate:
    date: _dt.date
    rate: Decimal
    is_weekend: bool


@dataclass
class PriceBreakdown:
    nights: int
    nightly_rates: List[NightlyRate]
    subtotal: Decimal
    taxes: Decimal
    discount: Decimal
    total: Decimal

    def as_dict(self):
        return {
            "nights": self.nights,
            "nightly_rates": [
                {
                    "date": nr.date.isoformat(),
                    "rate": str(nr.rate),
                    "is_weekend": nr.is_weekend,
                }
                for nr in self.nightly_rates
            ],
            "subtotal": str(self.subtotal),
            "taxes": str(self.taxes),
            "discount": str(self.discount),
            "total": str(self.total),
        }


class PricingService:
    """Pricing & tax calculations for a booking."""

    DEFAULT_TAX_RATE = Decimal("0.00")  # 0% by default; override via settings

    # ------------------------------------------------------------------ #
    @classmethod
    def breakdown(
        cls,
        room: Room,
        check_in: _dt.date,
        check_out: _dt.date,
        *,
        discount: Decimal = Decimal("0.00"),
        tax_rate: Decimal | None = None,
    ) -> PriceBreakdown:
        """Compute the full price breakdown for a stay."""
        if not (check_in and check_out) or check_out <= check_in:
            return PriceBreakdown(
                nights=0,
                nightly_rates=[],
                subtotal=Decimal("0.00"),
                taxes=Decimal("0.00"),
                discount=Decimal("0.00"),
                total=Decimal("0.00"),
            )

        nightly: List[NightlyRate] = []
        cursor = check_in
        subtotal = Decimal("0.00")
        while cursor < check_out:
            rate = room.get_nightly_rate(cursor)
            is_weekend = cursor.weekday() in (4, 5)
            nightly.append(NightlyRate(date=cursor, rate=rate, is_weekend=is_weekend))
            subtotal += Decimal(rate)
            cursor += _dt.timedelta(days=1)

        if tax_rate is None:
            tax_rate = cls.DEFAULT_TAX_RATE

        discount = Decimal(discount or 0)
        taxes = (subtotal - discount) * Decimal(tax_rate)
        total = (subtotal - discount) + taxes

        return PriceBreakdown(
            nights=len(nightly),
            nightly_rates=nightly,
            subtotal=subtotal.quantize(Decimal("0.01")),
            taxes=taxes.quantize(Decimal("0.01")),
            discount=discount.quantize(Decimal("0.01")),
            total=total.quantize(Decimal("0.01")),
        )

    # ------------------------------------------------------------------ #
    @classmethod
    def apply_to_booking(
        cls,
        booking,
        *,
        tax_rate: Decimal | None = None,
    ) -> None:
        """Mutates a Booking in place, filling in nights/rate/subtotal/total."""
        bd = cls.breakdown(
            booking.room,
            booking.check_in_date,
            booking.check_out_date,
            discount=booking.discount or Decimal("0.00"),
            tax_rate=tax_rate,
        )
        booking.nights = bd.nights
        booking.room_rate = bd.nightly_rates[0].rate if bd.nightly_rates else Decimal("0.00")
        booking.subtotal = bd.subtotal
        booking.taxes = bd.taxes
        booking.total_amount = bd.total
