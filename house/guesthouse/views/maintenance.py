"""Room maintenance views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from guesthouse.forms.maintenance import RoomMaintenanceForm
from guesthouse.models import Room, RoomMaintenance
from guesthouse.views._common import (
    admin_or_manager_required,
    maintenance_only_required,
    render_gh,
    role_required,
)


@role_required()
@require_GET
def maintenance_list(request):
    qs = RoomMaintenance.objects.select_related("room", "assigned_to", "reported_by")
    status = request.GET.get("status", "")
    priority = request.GET.get("priority", "")
    if status:
        qs = qs.filter(status=status)
    if priority:
        qs = qs.filter(priority=priority)
    return render_gh(
        request,
        "guesthouse/maintenance/maintenance_list.html",
        {
            "issues": qs.order_by("-reported_date")[:200],
            "status_choices": RoomMaintenance.STATUS_CHOICES,
            "priority_choices": RoomMaintenance.PRIORITY_CHOICES,
            "rooms": Room.objects.filter(active=True),
            "status_filter": status,
            "priority_filter": priority,
            "active_nav": "maintenance",
        },
    )


@role_required()
@require_http_methods(["GET", "POST"])
def maintenance_create(request):
    form = RoomMaintenanceForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        issue = form.save(commit=False)
        issue.reported_by = request.user
        issue.save()
        messages.success(request, "Maintenance issue logged.")
        return redirect("guesthouse:maintenance_list")
    return render_gh(
        request,
        "guesthouse/maintenance/maintenance_form.html",
        {"form": form, "active_nav": "maintenance"},
    )


@maintenance_only_required
@require_http_methods(["GET", "POST"])
def maintenance_edit(request, pk):
    issue = get_object_or_404(RoomMaintenance, pk=pk)
    form = RoomMaintenanceForm(request.POST or None, instance=issue)
    if request.method == "POST" and form.is_valid():
        i = form.save(commit=False)
        if i.status in (RoomMaintenance.STATUS_RESOLVED, RoomMaintenance.STATUS_CLOSED):
            if not i.resolved_date:
                i.resolved_date = timezone.now()
        i.save()
        messages.success(request, "Issue updated.")
        return redirect("guesthouse:maintenance_list")
    return render_gh(
        request,
        "guesthouse/maintenance/maintenance_form.html",
        {"form": form, "issue": issue, "active_nav": "maintenance"},
    )


@admin_or_manager_required
@require_POST
def maintenance_delete(request, pk):
    issue = get_object_or_404(RoomMaintenance, pk=pk)
    issue.delete()
    messages.success(request, "Issue deleted.")
    return redirect("guesthouse:maintenance_list")
