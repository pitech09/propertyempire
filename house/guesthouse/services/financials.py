"""GuesthouseFinancials — calculate platform costs (owner share) for the
guesthouse, mirroring the rental side.

These helpers centralise the math so the dashboard, revenue report and any
other financial view show consistent numbers.

Rules (mirroring the rentals / landlord app):
- Platform (owner) transaction fee = ``PLATFORM_TRANSACTION_FEE_RATE`` × revenue
  (default 1%).
- Monthly subscription = ``LANDLORD_MONTHLY_SUBSCRIPTION`` (default M 200.00)
  charged per active month.
- Net after all fees = revenue − platform fee − monthly subscription.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal
from typing import Iterable, Optional

from django.conf import settings
from django.db.models import QuerySet, Sum

from guesthouse.models import GuestPayment


def _q(value) -> Decimal:
    """Coerce None / numeric to a 2-dp Decimal."""
    return (value or Decimal("0.00")).quantize(Decimal("0.01"))


def platform_transaction_fee_rate() -> Decimal:
    """Return the configured platform transaction fee rate (e.g. 0.01 = 1%)."""
    return Decimal(getattr(settings, "PLATFORM_TRANSACTION_FEE_RATE", "0.01"))


def monthly_subscription() -> Decimal:
    """Return the monthly subscription amount (e.g. M 200.00)."""
    return Decimal(getattr(settings, "LANDLORD_MONTHLY_SUBSCRIPTION", "200.00"))


def compute_platform_costs(
    revenue: Decimal,
    *,
    include_monthly_subscription: bool = True,
) -> dict:
    """Return the standard platform-cost breakdown for a given revenue figure.

    Returned keys:
        ``revenue``                — input revenue (Decimal, 2 dp)
        ``platform_fee``           — 1% of revenue
        ``monthly_subscription``   — flat M 200 (or 0 if disabled)
        ``net_after_fees``         — revenue − platform fee − monthly_subscription
    """
    revenue = _q(revenue)
    fee_rate = platform_transaction_fee_rate()
    platform_fee = _q(revenue * fee_rate)
    sub = monthly_subscription() if include_monthly_subscription else Decimal("0.00")
    sub = _q(sub)
    net_after_fees = _q(revenue - platform_fee - sub)
    return {
        "revenue": revenue,
        "platform_fee": platform_fee,
        "monthly_subscription": sub,
        "net_after_fees": net_after_fees,
        "transaction_fee_rate": fee_rate,
    }


def summarize_payments(
    payments: QuerySet | Iterable[GuestPayment],
) -> dict:
    """Run a payments iterable / queryset through the platform-cost breakdown."""
    if isinstance(payments, QuerySet):
        revenue = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    else:
        revenue = sum((p.amount for p in payments), Decimal("0.00"))
    return compute_platform_costs(revenue)


def period_revenue(
    start_date: _dt.date,
    end_date: _dt.date,
    *,
    room_type_id: Optional[int] = None,
) -> Decimal:
    """Total revenue (sum of payments) within a date window, optionally
    filtered by room type."""
    qs = GuestPayment.objects.filter(
        payment_date__date__gte=start_date,
        payment_date__date__lte=end_date,
    )
    if room_type_id:
        qs = qs.filter(booking__room__room_type_id=room_type_id)
    return _q(qs.aggregate(total=Sum("amount"))["total"])
