"""ReportingService — aggregations for the dashboard & reports screens."""

from __future__ import annotations

import datetime as _dt
from collections import OrderedDict
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db.models import Count, Q, Sum
from django.utils import timezone

from guesthouse.models import (
    Booking,
    Guest,
    GuestPayment,
    HousekeepingTask,
    Room,
    RoomMaintenance,
)


class ReportingService:
    """Read-only data aggregations used by the dashboard and reports."""

    # ------------------------------------------------------------------ #
    # Dashboard tiles
    # ------------------------------------------------------------------ #
    @classmethod
    def dashboard_metrics(cls, today: Optional[_dt.date] = None) -> Dict:
        today = today or timezone.localdate()
        yesterday = today - _dt.timedelta(days=1)

        # Active rooms = active=true
        active_rooms = Room.objects.filter(active=True)
        occupied_rooms = active_rooms.filter(status=Room.STATUS_OCCUPIED).count()
        available_rooms = active_rooms.filter(status=Room.STATUS_AVAILABLE).count()
        reserved_rooms = active_rooms.filter(status=Room.STATUS_RESERVED).count()
        cleaning_rooms = active_rooms.filter(status=Room.STATUS_CLEANING).count()
        oos_rooms = active_rooms.filter(status=Room.STATUS_OUT_OF_SERVICE).count()
        maintenance_rooms = active_rooms.filter(status=Room.STATUS_MAINTENANCE).count()

        # Today's arrivals & departures
        arrivals_today = Booking.objects.filter(check_in_date=today).exclude(
            booking_status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW]
        )
        departures_today = Booking.objects.filter(check_out_date=today).exclude(
            booking_status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW]
        )
        pending_bookings = Booking.objects.filter(
            booking_status=Booking.STATUS_PENDING
        ).count()

        # Revenue today = payments logged today
        revenue_today = GuestPayment.objects.filter(
            payment_date__date=today
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Occupancy %
        total_rooms = active_rooms.count()
        occupancy_pct = (
            round((occupied_rooms / total_rooms) * 100, 1) if total_rooms else 0
        )

        # In-house guests
        in_house = Booking.objects.filter(
            booking_status=Booking.STATUS_CHECKED_IN
        ).aggregate(
            adults=Sum("adults"),
            children=Sum("children"),
        )
        in_house_adults = in_house.get("adults") or 0
        in_house_children = in_house.get("children") or 0

        return {
            "today": today.isoformat(),
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "available_rooms": available_rooms,
            "reserved_rooms": reserved_rooms,
            "cleaning_rooms": cleaning_rooms,
            "maintenance_rooms": maintenance_rooms,
            "out_of_service_rooms": oos_rooms,
            "occupancy_pct": occupancy_pct,
            "arrivals_today": list(arrivals_today.select_related("guest", "room")[:25]),
            "departures_today": list(departures_today.select_related("guest", "room")[:25]),
            "arrivals_count": arrivals_today.count(),
            "departures_count": departures_today.count(),
            "pending_bookings": pending_bookings,
            "revenue_today": revenue_today,
            "in_house_adults": in_house_adults,
            "in_house_children": in_house_children,
            "in_house_total": in_house_adults + in_house_children,
        }

    # ------------------------------------------------------------------ #
    # Occupancy
    # ------------------------------------------------------------------ #
    @classmethod
    def occupancy_for_range(
        cls,
        start_date: _dt.date,
        end_date: _dt.date,
    ) -> List[Dict]:
        """Per-day occupancy percentage between start and end (inclusive)."""
        if end_date < start_date:
            return []
        active_rooms = Room.objects.filter(active=True).count()
        data: List[Dict] = []
        cursor = start_date
        while cursor <= end_date:
            occupied = Booking.objects.filter(
                booking_status__in=[
                    Booking.STATUS_CHECKED_IN,
                    Booking.STATUS_CHECKED_OUT,
                    Booking.STATUS_CONFIRMED,
                ],
                check_in_date__lte=cursor,
                check_out_date__gt=cursor,
            ).count()
            pct = round((occupied / active_rooms) * 100, 1) if active_rooms else 0
            data.append(
                {
                    "date": cursor.isoformat(),
                    "occupied": occupied,
                    "total_rooms": active_rooms,
                    "occupancy_pct": pct,
                }
            )
            cursor += _dt.timedelta(days=1)
        return data

    # ------------------------------------------------------------------ #
    # Revenue
    # ------------------------------------------------------------------ #
    @classmethod
    def revenue_by_day(
        cls, start_date: _dt.date, end_date: _dt.date
    ) -> List[Dict]:
        payments = GuestPayment.objects.filter(
            payment_date__date__gte=start_date,
            payment_date__date__lte=end_date,
        ).values("payment_date__date").annotate(total=Sum("amount"))
        lookup = {p["payment_date__date"]: p["total"] for p in payments}
        data: List[Dict] = []
        cursor = start_date
        while cursor <= end_date:
            data.append(
                {
                    "date": cursor.isoformat(),
                    "revenue": float(lookup.get(cursor, Decimal("0.00"))),
                }
            )
            cursor += _dt.timedelta(days=1)
        return data

    @classmethod
    def revenue_by_room_type(
        cls, start_date: _dt.date, end_date: _dt.date
    ) -> List[Dict]:
        bookings = (
            Booking.objects.filter(
                booking_date__date__gte=start_date,
                booking_date__date__lte=end_date,
            )
            .exclude(booking_status=Booking.STATUS_CANCELLED)
            .values("room__room_type__name")
            .annotate(revenue=Sum("total_amount"), bookings=Count("id"))
            .order_by("-revenue")
        )
        return [
            {
                "room_type": b["room__room_type__name"] or "Unspecified",
                "revenue": float(b["revenue"] or 0),
                "bookings": b["bookings"],
            }
            for b in bookings
        ]

    @classmethod
    def revenue_by_source(
        cls, start_date: _dt.date, end_date: _dt.date
    ) -> List[Dict]:
        bookings = (
            Booking.objects.filter(
                booking_date__date__gte=start_date,
                booking_date__date__lte=end_date,
            )
            .exclude(booking_status=Booking.STATUS_CANCELLED)
            .values("booking_source")
            .annotate(revenue=Sum("total_amount"), bookings=Count("id"))
        )
        return [
            {
                "source": b["booking_source"],
                "label": dict(Booking.SOURCE_CHOICES).get(b["booking_source"], b["booking_source"]),
                "revenue": float(b["revenue"] or 0),
                "bookings": b["bookings"],
            }
            for b in bookings
        ]

    # ------------------------------------------------------------------ #
    # Calendar feed
    # ------------------------------------------------------------------ #
    @classmethod
    def calendar_events(
        cls, start_date: _dt.date, end_date: _dt.date
    ) -> List[Dict]:
        bookings = (
            Booking.objects.filter(
                check_in_date__lt=end_date + _dt.timedelta(days=1),
                check_out_date__gt=start_date,
            )
            .exclude(booking_status=Booking.STATUS_CANCELLED)
            .select_related("guest", "room", "room__room_type")
        )
        events: List[Dict] = []
        for b in bookings:
            events.append(
                {
                    "id": b.id,
                    "title": f"{b.guest.full_name} • Room {b.room.room_number}",
                    "start": b.check_in_date.isoformat(),
                    "end": b.check_out_date.isoformat(),
                    "status": b.booking_status,
                    "url": f"/guesthouse/bookings/{b.id}/",
                    "room_number": b.room.room_number,
                    "room_type": b.room.room_type.name,
                    "guest": b.guest.full_name,
                    "nights": b.nights,
                    "total": float(b.total_amount),
                    "color": {
                        Booking.STATUS_PENDING: "#f59e0b",
                        Booking.STATUS_CONFIRMED: "#3b82f6",
                        Booking.STATUS_CHECKED_IN: "#22c55e",
                        Booking.STATUS_CHECKED_OUT: "#64748b",
                        Booking.STATUS_NO_SHOW: "#ef4444",
                    }.get(b.booking_status, "#3b82f6"),
                }
            )
        return events
