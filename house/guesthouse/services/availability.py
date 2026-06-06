"""BookingAvailabilityService — prevents double-booking & overlap."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Iterable, List, Optional

from django.db.models import Q

from guesthouse.models import Booking, Room


@dataclass
class Conflict:
    """A single overlap between a candidate booking and an existing one."""

    booking: Booking
    overlap_start: _dt.date
    overlap_end: _dt.date

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"Conflict with {self.booking.booking_reference} "
            f"({self.overlap_start}  {self.overlap_end})"
        )


class BookingAvailabilityService:
    """All booking availability / conflict detection logic lives here.

    The service is *stateless*; methods are classmethods so it can be
    used from views, forms, and tests without instantiation.
    """

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @classmethod
    def is_room_available(
        cls,
        room: Room,
        check_in: _dt.date,
        check_out: _dt.date,
        *,
        exclude_booking_id: Optional[int] = None,
    ) -> bool:
        """Return True if a Room is free for the given date range.

        `check_out` is the day the guest leaves (the night of, not the
        morning of).  Two bookings collide if they share at least one
        night.
        """
        if not all([room, check_in, check_out]):
            return False
        if check_out <= check_in:
            return False
        return not cls.detect_conflicts(
            room, check_in, check_out, exclude_booking_id=exclude_booking_id
        )

    @classmethod
    def detect_conflicts(
        cls,
        room: Room,
        check_in: _dt.date,
        check_out: _dt.date,
        *,
        exclude_booking_id: Optional[int] = None,
    ) -> List[Conflict]:
        """Return a list of overlapping bookings for the room/dates."""
        if not all([room, check_in, check_out]) or check_out <= check_in:
            return []

        active_statuses = (
            Booking.STATUS_PENDING,
            Booking.STATUS_CONFIRMED,
            Booking.STATUS_CHECKED_IN,
        )

        qs = Booking.objects.filter(
            room=room,
            booking_status__in=active_statuses,
        ).filter(
            # Standard overlap predicate: existing.start < new.end
            # AND existing.end > new.start
            Q(check_in_date__lt=check_out) & Q(check_out_date__gt=check_in)
        )
        if exclude_booking_id is not None:
            qs = qs.exclude(pk=exclude_booking_id)

        conflicts: List[Conflict] = []
        for b in qs:
            overlap_start = max(b.check_in_date, check_in)
            overlap_end = min(b.check_out_date, check_out)
            conflicts.append(
                Conflict(
                    booking=b,
                    overlap_start=overlap_start,
                    overlap_end=overlap_end,
                )
            )
        return conflicts

    @classmethod
    def find_available_rooms(
        cls,
        check_in: _dt.date,
        check_out: _dt.date,
        *,
        guests: int = 1,
        room_type_id: Optional[int] = None,
        exclude_booking_id: Optional[int] = None,
    ) -> List[Room]:
        """Return rooms that have capacity >= guests and are free for the range."""
        if not (check_in and check_out) or check_out <= check_in:
            return []

        rooms = Room.objects.filter(active=True)
        if room_type_id:
            rooms = rooms.filter(room_type_id=room_type_id)
        if guests:
            rooms = rooms.filter(capacity__gte=guests)

        conflicting_room_ids = set(
            cls.detect_conflict_room_ids(
                check_in, check_out, exclude_booking_id=exclude_booking_id
            )
        )
        return [r for r in rooms if r.id not in conflicting_room_ids]

    @classmethod
    def detect_conflict_room_ids(
        cls,
        check_in: _dt.date,
        check_out: _dt.date,
        *,
        exclude_booking_id: Optional[int] = None,
    ) -> Iterable[int]:
        """Return a set/iterable of room_ids that have overlapping bookings."""
        if not (check_in and check_out) or check_out <= check_in:
            return set()
        active_statuses = (
            Booking.STATUS_PENDING,
            Booking.STATUS_CONFIRMED,
            Booking.STATUS_CHECKED_IN,
        )
        qs = Booking.objects.filter(
            booking_status__in=active_statuses,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        )
        if exclude_booking_id is not None:
            qs = qs.exclude(pk=exclude_booking_id)
        return list(qs.values_list("room_id", flat=True).distinct())

    @classmethod
    def next_available_date(
        cls, room: Room, start_date: _dt.date, *, max_days: int = 60
    ) -> _dt.date:
        """Return the next date the room becomes available, scanning forward."""
        cursor = start_date
        for _ in range(max_days):
            if cls.is_room_available(room, cursor, cursor + _dt.timedelta(days=1)):
                return cursor
            cursor += _dt.timedelta(days=1)
        return cursor
