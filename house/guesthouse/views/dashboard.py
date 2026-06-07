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
from guesthouse.services.financials import (
    compute_platform_costs,
    monthly_subscription,
    period_revenue,
    platform_transaction_fee_rate,
)
from guesthouse.services.reporting import ReportingService
from guesthouse.views._common import render_gh, role_required


def _to_chart_points(rows, *, value_key: str, label_fmt: str = "%b %d") -> list:
    """Normalize reporting service rows to {label, value} for Chart.js."""
    import datetime as _dt

    points = []
    for row in rows:
        d = row.get("date")
        if isinstance(d, str):
            try:
                d = _dt.date.fromisoformat(d)
            except ValueError:
                pass
        if isinstance(d, _dt.date):
            label = d.strftime(label_fmt)
        else:
            label = str(d) if d is not None else ""
        try:
            value = float(row.get(value_key) or 0)
        except (TypeError, ValueError):
            value = 0.0
        points.append({"label": label, "value": round(value, 2)})
    return points


@role_required()
@require_GET
def dashboard(request):
    metrics = ReportingService.dashboard_metrics()
    today = timezone.localdate()
    month_start = today.replace(day=1)

    # ---- Last 14 days occupancy for sparkline ----
    start_occ = today - timezone.timedelta(days=13)
    occupancy_data = _to_chart_points(
        ReportingService.occupancy_for_range(start_occ, today),
        value_key="occupancy_pct",
    )

    # ---- Last 14 days revenue ----
    revenue_data = _to_chart_points(
        ReportingService.revenue_by_day(start_occ, today),
        value_key="revenue",
    )

    # ---- Top booking sources (last 30 days) ----
    rev_sources_rows = ReportingService.revenue_by_source(
        today - timezone.timedelta(days=30), today
    )
    rev_sources = {
        row.get("label") or row.get("source") or "Other": float(
            row.get("revenue") or 0
        )
        for row in rev_sources_rows
    }

    # ---- Room type performance (last 30 days) ----
    rev_room_types_rows = ReportingService.revenue_by_room_type(
        today - timezone.timedelta(days=30), today
    )
    rev_room_types = {
        row.get("room_type") or "Unspecified": float(row.get("revenue") or 0)
        for row in rev_room_types_rows
    }

    # ---- Financial summaries (month-to-date) ----
    mtd_revenue_qs = GuestPayment.objects.filter(
        payment_date__date__gte=month_start,
        payment_date__date__lte=today,
    )
    mtd_revenue = mtd_revenue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    mtd_payment_count = mtd_revenue_qs.count()

    # ---- All-time revenue + platform cost breakdown ----
    total_revenue_qs = GuestPayment.objects.all()
    total_revenue = (
        total_revenue_qs.aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    # MTD and all-time platform-cost calculations
    mtd_platform = compute_platform_costs(mtd_revenue)
    total_platform = compute_platform_costs(total_revenue)
    # Count active months for MTD subscription (1, 2, ... up to current month)
    months_active = (today.year - month_start.year) * 12 + (
        today.month - month_start.month + 1
    )
    if months_active < 1:
        months_active = 1
    mtd_subscription = (
        Decimal(months_active) * monthly_subscription()
    ).quantize(Decimal("0.01"))
    # For the all-time snapshot we charge a single monthly sub (current month)
    total_subscription = monthly_subscription()
    mtd_net = (
        mtd_revenue - mtd_platform["platform_fee"] - mtd_subscription
    ).quantize(Decimal("0.01"))
    total_net = (
        total_revenue - total_platform["platform_fee"] - total_subscription
    ).quantize(Decimal("0.01"))

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

    # ---- Detect "no data" state so the dashboard prompts setup ----
    no_data_reasons = []
    if Room.objects.count() == 0:
        no_data_reasons.append("No rooms yet")
    if not rev_sources:
        no_data_reasons.append("No bookings in the last 30 days")
    if mtd_payment_count == 0:
        no_data_reasons.append("No payments this month")
    no_data_mode = len(no_data_reasons) >= 2

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
        # Platform / owner costs (mirrors landlord dashboard)
        "total_revenue": total_revenue,
        "transaction_fee_rate": platform_transaction_fee_rate(),
        "mtd_platform_fee": mtd_platform["platform_fee"],
        "total_platform_fee": total_platform["platform_fee"],
        "mtd_subscription": mtd_subscription,
        "monthly_subscription": total_subscription,
        "mtd_net_after_fees": mtd_net,
        "total_net_after_fees": total_net,
        "months_active": months_active,
        # Quick action counts
        "pending_payments": pending_payments,
        "unpaid_balance_count": unpaid_balance_count,
        "pending_housekeeping": pending_housekeeping,
        "pending_maintenance": pending_maintenance,
        # Empty-state hints
        "no_data_mode": no_data_mode,
        "no_data_reasons": no_data_reasons,
        "active_nav": "dashboard",
    }
    return render_gh(request, "guesthouse/dashboard.html", context)
