"""Guesthouse dashboard view."""

import json
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from guesthouse.models import (
    Booking,
    GuestPayment,
    HousekeepingTask,
    Room,
    RoomMaintenance,
)
from guesthouse.services.reporting import ReportingService
from guesthouse.views._common import render_gh, role_required


@role_required()
@require_GET
def dashboard(request):
    metrics = ReportingService.dashboard_metrics()
    today = timezone.localdate()
    month_start = today.replace(day=1)

    # ---- Last 14 days occupancy for sparkline ----
    start_occ = today - timezone.timedelta(days=13)
    occupancy_data = ReportingService.occupancy_for_range(start_occ, today)

    # ---- Last 14 days revenue ----
    revenue_data = ReportingService.revenue_by_day(start_occ, today)

    # ---- Top booking sources (last 30 days) ----
    rev_sources = ReportingService.revenue_by_source(
        today - timezone.timedelta(days=30), today
    )

    # ---- Room type performance (last 30 days) ----
    rev_room_types = ReportingService.revenue_by_room_type(
        today - timezone.timedelta(days=30), today
    )

    # ---- Financial summaries (month-to-date) ----
    mtd_revenue_qs = GuestPayment.objects.filter(
        payment_date__date__gte=month_start,
        payment_date__date__lte=today,
    )
    mtd_revenue = mtd_revenue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    mtd_payment_count = mtd_revenue_qs.count()

    # Outstanding balances across all non-cancelled bookings
    active_bookings = Booking.objects.exclude(
        booking_status__in=[Booking.STATUS_CANCELLED, Booking.STATUS_NO_SHOW]
    )
    outstanding_balance = Decimal("0.00")
    unpaid_balance_count = 0
    checked_in_count = 0
    for b in active_bookings.only(
        "total_amount", "extra_charges", "amount_paid", "booking_status"
    ):
        balance = (
            (b.total_amount or 0)
            + (b.extra_charges or 0)
            - (b.amount_paid or 0)
        )
        outstanding_balance += balance
        if balance > 0:
            unpaid_balance_count += 1
        if b.booking_status == Booking.STATUS_CHECKED_IN:
            checked_in_count += 1

    # Average Daily Rate (ADR) over last 30 days from non-cancelled bookings
    recent_bookings = Booking.objects.filter(
        check_in_date__gte=today - timezone.timedelta(days=30),
    ).exclude(booking_status=Booking.STATUS_CANCELLED)
    total_room_revenue = sum(
        (b.total_amount or 0) for b in recent_bookings
    )
    total_room_nights = sum((b.nights or 0) for b in recent_bookings)
    adr = float(total_room_revenue / total_room_nights) if total_room_nights else 0.0

    # RevPAR (Revenue per available room) for the same window
    available_rooms = Room.objects.filter(active=True).count()
    revpar = float(total_room_revenue / (available_rooms * 30)) if available_rooms else 0.0

    # 30-day projection: today's revenue * 30 (rough)
    today_revenue = GuestPayment.objects.filter(
        payment_date__date=today
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    projected_30d = float(today_revenue) * 30

    # ---- Quick action counts ----
    pending_payments = Booking.objects.filter(
        booking_status=Booking.STATUS_CHECKED_OUT
    ).count()  # checked out but not yet fully reconciled
    pending_housekeeping = HousekeepingTask.objects.exclude(
        status=HousekeepingTask.STATUS_COMPLETED
    ).count()
    pending_maintenance = RoomMaintenance.objects.exclude(
        status=RoomMaintenance.STATUS_RESOLVED
    ).count()

    context = {
        "metrics": metrics,
        "occupancy_data": json.dumps(occupancy_data),
        "revenue_data": json.dumps(revenue_data),
        "rev_sources": json.dumps(rev_sources),
        "rev_room_types": json.dumps(rev_room_types),
        # Financial
        "mtd_revenue": mtd_revenue,
        "mtd_payment_count": mtd_payment_count,
        "outstanding_balance": outstanding_balance,
        "checked_in_count": checked_in_count,
        "adr": adr,
        "revpar": revpar,
        "projected_30d": projected_30d,
        # Quick action counts
        "pending_payments": pending_payments,
        "unpaid_balance_count": unpaid_balance_count,
        "pending_housekeeping": pending_housekeeping,
        "pending_maintenance": pending_maintenance,
        "active_nav": "dashboard",
    }
    return render_gh(request, "guesthouse/dashboard.html", context)
