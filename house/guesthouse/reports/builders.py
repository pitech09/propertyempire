"""Report builders — produce querysets and aggregates for the four reports."""

from __future__ import annotations

import datetime as _dt
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, List, Tuple

from django.db.models import Count, Q, Sum
from django.utils import timezone

from guesthouse.models import (
    Booking,
    Guest,
    GuestPayment,
    Room,
    RoomMaintenance,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_range(
    period: str, start: _dt.date | None, end: _dt.date | None
) -> Tuple[_dt.date, _dt.date]:
    today = timezone.localdate()
    if period == "day" or (start and end and start == end):
        return today, today
    if period == "week":
        start_of_week = today - _dt.timedelta(days=today.weekday())
        return start_of_week, start_of_week + _dt.timedelta(days=6)
    if period == "month":
        return today.replace(day=1), today
    if period == "year":
        return today.replace(month=1, day=1), today
    if start and end:
        return start, end
    return today.replace(day=1), today


# ---------------------------------------------------------------------------
# Occupancy
# ---------------------------------------------------------------------------
def build_occupancy_report(
    period: str = "month",
    start: _dt.date | None = None,
    end: _dt.date | None = None,
):
    start_d, end_d = _resolve_range(period, start, end)
    total_rooms = Room.objects.filter(active=True).count()
    days: List[Dict] = []
    cursor = start_d
    while cursor <= end_d:
        occupied = Booking.objects.filter(
            booking_status__in=[
                Booking.STATUS_CHECKED_IN,
                Booking.STATUS_CHECKED_OUT,
                Booking.STATUS_CONFIRMED,
            ],
            check_in_date__lte=cursor,
            check_out_date__gt=cursor,
        ).count()
        # In-house guest counts
        guests = Booking.objects.filter(
            booking_status=Booking.STATUS_CHECKED_IN,
            check_in_date__lte=cursor,
            check_out_date__gt=cursor,
        ).aggregate(a=Sum("adults"), c=Sum("children"))
        days.append(
            {
                "date": cursor,
                "occupied": occupied,
                "available": max(0, total_rooms - occupied),
                "occupancy_pct": round((occupied / total_rooms) * 100, 1)
                if total_rooms
                else 0,
                "adults": guests.get("a") or 0,
                "children": guests.get("c") or 0,
            }
        )
        cursor += _dt.timedelta(days=1)
    avg_occupancy = (
        sum(d["occupancy_pct"] for d in days) / len(days) if days else 0
    )
    return {
        "period": period,
        "start": start_d,
        "end": end_d,
        "total_rooms": total_rooms,
        "days": days,
        "average_occupancy": round(avg_occupancy, 1),
    }


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------
def build_revenue_report(
    start: _dt.date | None = None,
    end: _dt.date | None = None,
    room_type_id: int | None = None,
):
    start_d, end_d = _resolve_range("custom", start, end)
    qs = GuestPayment.objects.filter(
        payment_date__date__gte=start_d,
        payment_date__date__lte=end_d,
    ).select_related("booking", "booking__room", "booking__room__room_type")

    if room_type_id:
        qs = qs.filter(booking__room__room_type_id=room_type_id)

    total_revenue = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    by_method = list(
        qs.values("payment_method")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )
    by_day: Dict[_dt.date, Decimal] = OrderedDict()
    cursor = start_d
    while cursor <= end_d:
        by_day[cursor] = Decimal("0.00")
        cursor += _dt.timedelta(days=1)
    for p in qs:
        d = p.payment_date.date()
        if d in by_day:
            by_day[d] += p.amount
    return {
        "start": start_d,
        "end": end_d,
        "total_revenue": total_revenue,
        "payments_count": qs.count(),
        "by_method": by_method,
        "by_day": [{"date": d, "revenue": float(v)} for d, v in by_day.items()],
    }


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------
def build_booking_report(
    start: _dt.date | None = None,
    end: _dt.date | None = None,
    source: str | None = None,
    status: str | None = None,
):
    start_d, end_d = _resolve_range("custom", start, end)
    qs = Booking.objects.filter(
        booking_date__date__gte=start_d,
        booking_date__date__lte=end_d,
    ).select_related("guest", "room", "room__room_type")
    if source:
        qs = qs.filter(booking_source=source)
    if status:
        qs = qs.filter(booking_status=status)
    summary = qs.aggregate(
        total=Count("id"),
        revenue=Sum("total_amount"),
        nights=Sum("nights"),
    )
    by_status = list(
        qs.values("booking_status").annotate(count=Count("id"))
    )
    by_source = list(
        qs.values("booking_source").annotate(
            count=Count("id"), revenue=Sum("total_amount")
        )
    )
    return {
        "start": start_d,
        "end": end_d,
        "summary": {
            "total": summary.get("total") or 0,
            "revenue": summary.get("revenue") or Decimal("0.00"),
            "nights": summary.get("nights") or 0,
        },
        "by_status": by_status,
        "by_source": by_source,
        "bookings": qs.order_by("-check_in_date"),
    }


# ---------------------------------------------------------------------------
# Guest history
# ---------------------------------------------------------------------------
def build_guest_history_report(
    limit: int = 50,
    sort: str = "total_spent",
):
    guests = Guest.objects.all()
    history = []
    for g in guests:
        bookings = g.bookings.all()
        completed = bookings.filter(
            booking_status=Booking.STATUS_CHECKED_OUT
        )
        total_spent = GuestPayment.objects.filter(
            booking__guest=g
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        history.append(
            {
                "guest": g,
                "total_stays": completed.count(),
                "total_bookings": bookings.count(),
                "total_nights": completed.aggregate(n=Sum("nights"))["n"] or 0,
                "total_spent": total_spent,
                "last_stay_at": g.last_stay_at,
            }
        )
    reverse = sort != "name"
    history.sort(
        key=lambda h: (
            -float(h["total_spent"])
            if sort == "total_spent"
            else -h["total_stays"]
            if sort == "total_stays"
            else h["guest"].full_name.lower()
        ),
        reverse=reverse if sort == "name" else False,
    )
    return {
        "history": history[:limit],
        "total_guests": len(history),
    }
