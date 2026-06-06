"""Guesthouse dashboard view."""

import json

from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from guesthouse.services.reporting import ReportingService
from guesthouse.views._common import render_gh, role_required


@role_required()
@require_GET
def dashboard(request):
    metrics = ReportingService.dashboard_metrics()
    today = timezone.localdate()

    # Last 14 days occupancy for sparkline
    start_occ = today - timezone.timedelta(days=13)
    occupancy_data = ReportingService.occupancy_for_range(start_occ, today)

    # Last 14 days revenue
    revenue_data = ReportingService.revenue_by_day(start_occ, today)

    # Top booking sources (last 30 days)
    rev_sources = ReportingService.revenue_by_source(
        today - timezone.timedelta(days=30), today
    )

    # Room type performance (last 30 days)
    rev_room_types = ReportingService.revenue_by_room_type(
        today - timezone.timedelta(days=30), today
    )

    context = {
        "metrics": metrics,
        "occupancy_data": json.dumps(occupancy_data),
        "revenue_data": json.dumps(revenue_data),
        "rev_sources": json.dumps(rev_sources),
        "rev_room_types": json.dumps(rev_room_types),
        "active_nav": "dashboard",
    }
    return render_gh(request, "guesthouse/dashboard.html", context)
