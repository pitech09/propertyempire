"""Reports views — occupancy, revenue, bookings, guest history."""

import datetime as _dt

from django.utils import timezone
from django.views.decorators.http import require_GET

from guesthouse.models import Booking, RoomType
from guesthouse.reports.builders import (
    build_booking_report,
    build_guest_history_report,
    build_occupancy_report,
    build_revenue_report,
)
from guesthouse.views._common import render_gh, role_required


@role_required()
@require_GET
def report_index(request):
    return render_gh(
        request,
        "guesthouse/reports/index.html",
        {"active_nav": "reports"},
    )


@role_required()
@require_GET
def occupancy_report(request):
    period = request.GET.get("period", "month")
    start, end = _parse_date_range(request)
    data = build_occupancy_report(period=period, start=start, end=end)
    return render_gh(
        request,
        "guesthouse/reports/occupancy.html",
        {
            "data": data,
            "period": period,
            "start": data["start"],
            "end": data["end"],
            "active_nav": "reports",
        },
    )


@role_required()
@require_GET
def revenue_report(request):
    start, end = _parse_date_range(request)
    room_type_id = request.GET.get("room_type") or None
    if room_type_id:
        try:
            room_type_id = int(room_type_id)
        except (TypeError, ValueError):
            room_type_id = None
    data = build_revenue_report(
        start=start, end=end, room_type_id=room_type_id
    )
    return render_gh(
        request,
        "guesthouse/reports/revenue.html",
        {
            "data": data,
            "room_types": RoomType.objects.filter(is_active=True),
            "selected_room_type": room_type_id,
            "start": data["start"],
            "end": data["end"],
            "active_nav": "reports",
        },
    )


@role_required()
@require_GET
def booking_report(request):
    start, end = _parse_date_range(request)
    source = request.GET.get("source") or None
    status = request.GET.get("status") or None
    data = build_booking_report(
        start=start, end=end, source=source, status=status
    )
    return render_gh(
        request,
        "guesthouse/reports/bookings.html",
        {
            "data": data,
            "source_choices": Booking.SOURCE_CHOICES,
            "status_choices": Booking.STATUS_CHOICES,
            "selected_source": source,
            "selected_status": status,
            "start": data["start"],
            "end": data["end"],
            "active_nav": "reports",
        },
    )


@role_required()
@require_GET
def guest_history_report(request):
    sort = request.GET.get("sort", "total_spent")
    data = build_guest_history_report(sort=sort, limit=200)
    return render_gh(
        request,
        "guesthouse/reports/guest_history.html",
        {"data": data, "sort": sort, "active_nav": "reports"},
    )


# --------------------------------------------------------------------- #
def _parse_date_range(request):
    start = request.GET.get("start")
    end = request.GET.get("end")
    try:
        start = _dt.date.fromisoformat(start) if start else None
    except (TypeError, ValueError):
        start = None
    try:
        end = _dt.date.fromisoformat(end) if end else None
    except (TypeError, ValueError):
        end = None
    if not start and not end:
        today = timezone.localdate()
        start = today.replace(day=1)
        end = today
    elif start and not end:
        end = start
    elif end and not start:
        start = end
    return start, end
