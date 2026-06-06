"""Housekeeping task views."""

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from guesthouse.forms.housekeeping import HousekeepingTaskForm
from guesthouse.models import HousekeepingTask, Room
from guesthouse.views._common import (
    admin_or_manager_required,
    housekeeping_only_required,
    render_gh,
    role_required,
)


@role_required()
@require_GET
def task_list(request):
    qs = HousekeepingTask.objects.select_related("room", "assigned_to")
    status = request.GET.get("status", "")
    room_id = request.GET.get("room", "")
    if status:
        qs = qs.filter(status=status)
    if room_id:
        qs = qs.filter(room_id=room_id)
    return render_gh(
        request,
        "guesthouse/housekeeping/task_list.html",
        {
            "tasks": qs.order_by("-scheduled_date", "room__room_number")[:200],
            "status_choices": HousekeepingTask.STATUS_CHOICES,
            "task_type_choices": HousekeepingTask.TASK_TYPE_CHOICES,
            "rooms": Room.objects.filter(active=True),
            "status_filter": status,
            "room_filter": room_id,
            "active_nav": "housekeeping",
        },
    )


@role_required()
@require_http_methods(["GET", "POST"])
def task_create(request):
    form = HousekeepingTaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save()
        messages.success(request, "Task created.")
        return redirect("guesthouse:task_list")
    return render_gh(
        request,
        "guesthouse/housekeeping/task_form.html",
        {"form": form, "active_nav": "housekeeping"},
    )


@housekeeping_only_required
@require_http_methods(["GET", "POST"])
def task_edit(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    form = HousekeepingTaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        # Auto-stamp when status flips to in_progress / completed
        if (
            t.status == HousekeepingTask.STATUS_IN_PROGRESS
            and not t.started_at
        ):
            t.started_at = timezone.now()
        if t.status == HousekeepingTask.STATUS_COMPLETED and not t.completed_date:
            t.completed_date = timezone.now()
        t.save()
        messages.success(request, "Task updated.")
        return redirect("guesthouse:task_list")
    return render_gh(
        request,
        "guesthouse/housekeeping/task_form.html",
        {"form": form, "task": task, "active_nav": "housekeeping"},
    )


@housekeeping_only_required
@require_POST
def task_complete(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    task.status = HousekeepingTask.STATUS_COMPLETED
    task.completed_date = timezone.now()
    if not task.started_at:
        task.started_at = task.completed_date
    task.save()
    # Move the room back to Available after cleaning
    if task.room.status == Room.STATUS_CLEANING:
        task.room.status = Room.STATUS_AVAILABLE
        task.room.save(update_fields=["status", "updated_at"])
    messages.success(request, "Task completed and room marked as available.")
    return redirect("guesthouse:task_list")


@admin_or_manager_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(HousekeepingTask, pk=pk)
    task.delete()
    messages.success(request, "Task deleted.")
    return redirect("guesthouse:task_list")
