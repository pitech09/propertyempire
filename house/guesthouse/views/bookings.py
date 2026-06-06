"""Booking CRUD + calendar views."""

import json
from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET

from guesthouse.forms.bookings import BookingForm
from guesthouse.models import Booking, Room
from guesthouse.services.availability import BookingAvailabilityService
from guesthouse.services.booking_service import BookingError, BookingService
from guesthouse.services.pricing import PricingService
from guesthouse.services.reporting import ReportingService
from guesthouse.views._common import (
    admin_or_manager_required,
    json_response,
    reception_or_above_required,
    render_gh,
    role_required,
)


# ------------------------------------------------------------------ #
# Calendar
# ------------------------------------------------------------------ #
@role_required()
@require_GET
def calendar_view(request):
    rooms = Room.objects.filter(active=True).select_related("room_type")
    return render_gh(
        request,
        "guesthouse/bookings/calendar.html",
        {
            "rooms": rooms,
            "active_nav": "calendar",
        },
    )


@role_required()
@require_GET
def calendar_events(request):
    import datetime as _dt
    try:
        start = _dt.date.fromisoformat(request.GET.get("start", ""))
        end = _dt.date.fromisoformat(request.GET.get("end", ""))
    except (ValueError, TypeError):
        today = timezone.localdate()
        start = today.replace(day=1)
        # End of next month
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)
    events = ReportingService.calendar_events(start, end)
    return json_response(events)


# ------------------------------------------------------------------ #
# Booking list / detail / edit
# ------------------------------------------------------------------ #
@role_required()
@require_GET
def booking_list(request):
    qs = Booking.objects.select_related("guest", "room", "room__room_type")
    status = request.GET.get("status", "")
    source = request.GET.get("source", "")
    q = request.GET.get("q", "").strip()
    if status:
        qs = qs.filter(booking_status=status)
    if source:
        qs = qs.filter(booking_source=source)
    if q:
        qs = qs.filter(
            Q(guest__first_name__icontains=q)
            | Q(guest__last_name__icontains=q)
            | Q(booking_reference__icontains=q)
            | Q(room__room_number__icontains=q)
        )
    return render_gh(
        request,
        "guesthouse/bookings/booking_list.html",
        {
            "bookings": qs.order_by("-check_in_date")[:200],
            "status_choices": Booking.STATUS_CHOICES,
            "source_choices": Booking.SOURCE_CHOICES,
            "status_filter": status,
            "source_filter": source,
            "q": q,
            "active_nav": "bookings",
        },
    )


@reception_or_above_required
@require_http_methods(["GET", "POST"])
def booking_create(request):
    form = BookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            booking = BookingService.create_booking(
                guest=form.cleaned_data["guest"],
                room=form.cleaned_data["room"],
                check_in=form.cleaned_data["check_in_date"],
                check_out=form.cleaned_data["check_out_date"],
                adults=form.cleaned_data.get("adults") or 1,
                children=form.cleaned_data.get("children") or 0,
                booking_source=form.cleaned_data.get(
                    "booking_source", Booking.SOURCE_WALK_IN
                ),
                discount=form.cleaned_data.get("discount") or 0,
                special_requests=form.cleaned_data.get("special_requests", ""),
                internal_notes=form.cleaned_data.get("internal_notes", ""),
                by_user=request.user,
                status=form.cleaned_data.get(
                    "booking_status", Booking.STATUS_CONFIRMED
                ),
            )
        except BookingError as e:
            messages.error(request, str(e))
        else:
            messages.success(
                request, f"Booking {booking.booking_reference} created."
            )
            return redirect("guesthouse:booking_detail", pk=booking.pk)
    return render_gh(
        request,
        "guesthouse/bookings/booking_form.html",
        {"form": form, "active_nav": "bookings"},
    )


@role_required()
@require_GET
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "guest", "room", "room__room_type", "stay"
        ),
        pk=pk,
    )
    payments = booking.payments.all().order_by("-payment_date")
    pricing = PricingService.breakdown(
        booking.room, booking.check_in_date, booking.check_out_date,
        discount=booking.discount or 0,
    )
    return render_gh(
        request,
        "guesthouse/bookings/booking_detail.html",
        {
            "booking": booking,
            "payments": payments,
            "pricing": pricing,
            "active_nav": "bookings",
        },
    )


@reception_or_above_required
@require_http_methods(["GET", "POST"])
def booking_edit(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    form = BookingForm(request.POST or None, instance=booking)
    if request.method == "POST" and form.is_valid():
        try:
            updated = BookingService.create_booking(
                guest=form.cleaned_data["guest"],
                room=form.cleaned_data["room"],
                check_in=form.cleaned_data["check_in_date"],
                check_out=form.cleaned_data["check_out_date"],
                adults=form.cleaned_data.get("adults") or 1,
                children=form.cleaned_data.get("children") or 0,
                booking_source=form.cleaned_data.get("booking_source"),
                discount=form.cleaned_data.get("discount") or 0,
                special_requests=form.cleaned_data.get("special_requests", ""),
                internal_notes=form.cleaned_data.get("internal_notes", ""),
                by_user=request.user,
                status=form.cleaned_data.get("booking_status"),
                skip_availability_check=False,
            )
        except BookingError as e:
            messages.error(request, str(e))
        else:
            # Preserve original ID and created_at
            updated.created_at = booking.created_at
            updated.save(update_fields=["created_at"])
            messages.success(
                request, f"Booking {updated.booking_reference} updated."
            )
            return redirect("guesthouse:booking_detail", pk=updated.pk)
    pricing = PricingService.breakdown(
        booking.room, booking.check_in_date, booking.check_out_date,
        discount=booking.discount or 0,
    )
    return render_gh(
        request,
        "guesthouse/bookings/booking_form.html",
        {
            "form": form,
            "booking": booking,
            "pricing": pricing,
            "active_nav": "bookings",
        },
    )


@admin_or_manager_required
@require_POST
def booking_delete(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.delete()
    messages.success(request, "Booking deleted.")
    return redirect("guesthouse:booking_list")


@reception_or_above_required
@require_POST
def booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    reason = request.POST.get("reason", "")
    try:
        BookingService.cancel_booking(booking, reason=reason, by_user=request.user)
        messages.success(request, f"Booking {booking.booking_reference} cancelled.")
    except BookingError as e:
        messages.error(request, str(e))
    return redirect("guesthouse:booking_detail", pk=booking.pk)


@reception_or_above_required
@require_POST
def booking_confirm(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    booking.confirm(by_user=request.user)
    messages.success(request, "Booking confirmed.")
    return redirect("guesthouse:booking_detail", pk=booking.pk)
