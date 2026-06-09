"""Shared helpers for guesthouse views.

- Permission decorators
- Context processors / mixins
- Common HTTP helpers
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from guesthouse.models import Booking


# ---------------------------------------------------------------------------
# Permissions / roles
# ---------------------------------------------------------------------------
ROLE_ADMIN = "Guesthouse Admin"
ROLE_PROPERTY_MANAGER = "Guesthouse Manager"
ROLE_RECEPTIONIST = "Guesthouse Receptionist"
ROLE_HOUSEKEEPER = "Guesthouse Housekeeper"
ROLE_MAINTENANCE = "Guesthouse Maintenance"

ALL_ROLES = (
    ROLE_ADMIN,
    ROLE_PROPERTY_MANAGER,
    ROLE_RECEPTIONIST,
    ROLE_HOUSEKEEPER,
    ROLE_MAINTENANCE,
)


def _user_in_group(user, group_names: Iterable[str]) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=list(group_names)).exists()


def role_required(*group_names: str) -> Callable:
    """Allow access to users in any of the named groups (or superuser)."""
    groups = tuple(group_names) or ALL_ROLES

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request: HttpRequest, *args, **kwargs):
            if not _user_in_group(request.user, groups):
                messages.error(
                    request,
                    "You do not have permission to access this section.",
                )
                return redirect("guesthouse:dashboard")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def admin_or_manager_required(view_func):
    return role_required(ROLE_ADMIN, ROLE_PROPERTY_MANAGER)(view_func)


def reception_or_above_required(view_func):
    return role_required(
        ROLE_ADMIN, ROLE_PROPERTY_MANAGER, ROLE_RECEPTIONIST
    )(view_func)


def maintenance_only_required(view_func):
    return role_required(
        ROLE_ADMIN, ROLE_PROPERTY_MANAGER, ROLE_MAINTENANCE
    )(view_func)


# ---------------------------------------------------------------------------
# AJAX helpers
# ---------------------------------------------------------------------------
def ajax_required(view_func):
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse(
                {"error": "AJAX required"}, status=400
            )
        return view_func(request, *args, **kwargs)

    return _wrapped


def json_response(data, *, status: int = 200) -> JsonResponse:
    return JsonResponse(data, status=status, safe=not isinstance(data, list))


# ---------------------------------------------------------------------------
# Common context
# ---------------------------------------------------------------------------
def base_context(request: HttpRequest, **extra) -> dict:
    """Standard context injected into every guesthouse template."""
    pending_count = 0
    if request.user.is_authenticated:
        pending_count = Booking.objects.filter(
            booking_status=Booking.STATUS_PENDING
        ).count()
    ctx = {
        "gh_nav": "guesthouse",
        "gh_pending_bookings": pending_count,
    }
    ctx.update(extra)
    return ctx


def render_gh(request: HttpRequest, template: str, context: dict | None = None) -> HttpResponse:
    ctx = base_context(request, **(context or {}))
    return render(request, template, ctx)
