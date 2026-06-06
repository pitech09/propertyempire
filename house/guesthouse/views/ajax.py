"""AJAX / JSON endpoints used by the dashboard and HTMX widgets."""

import datetime as _dt

from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_GET

from guesthouse.models import Booking, Room
from guesthouse.services.reporting import ReportingService
from guesthouse.views._common import (
    ajax_required,
    json_response,
    role_required,
)


@role_required()
@require_GET
def ajax_dashboard_metrics(request):
    data = ReportingService.dashboard_metrics()
    # Make datetime / Decimal serialisable
    data["arrivals_today"] = [
        {
            "id": b.id,
            "reference": b.booking_reference,
            "guest": b.guest.full_name,
            "room": b.room.room_number,
            "status": b.get_booking_status_display(),
        }
        for b in data["arrivals_today"]
    ]
    data["departures_today"] = [
        {
            "id": b.id,
            "reference": b.booking_reference,
            "guest": b.guest.full_name,
            "room": b.room.room_number,
            "status": b.get_booking_status_display(),
        }
        for b in data["departures_today"]
    ]
    data["revenue_today"] = float(data["revenue_today"])
    return json_response(data)


@role_required()
@require_GET
def ajax_rooms_occupancy(request):
    """Return current room status counts."""
    rooms = Room.objects.filter(active=True)
    data = {
        "total": rooms.count(),
        "available": rooms.filter(status=Room.STATUS_AVAILABLE).count(),
        "occupied": rooms.filter(status=Room.STATUS_OCCUPIED).count(),
        "reserved": rooms.filter(status=Room.STATUS_RESERVED).count(),
        "cleaning": rooms.filter(status=Room.STATUS_CLEANING).count(),
        "maintenance": rooms.filter(status=Room.STATUS_MAINTENANCE).count(),
        "out_of_service": rooms.filter(status=Room.STATUS_OUT_OF_SERVICE).count(),
    }
    return json_response(data)


@role_required()
@require_GET
@ajax_required
def ajax_booking_quick_status(request, pk):
    booking = Booking.objects.select_related("guest", "room").get(pk=pk)
    return json_response(
        {
            "id": booking.id,
            "reference": booking.booking_reference,
            "status": booking.booking_status,
            "status_display": booking.get_booking_status_display(),
            "balance": float(booking.balance),
            "total": float(booking.total_amount),
            "paid": float(booking.amount_paid),
        }
    )
