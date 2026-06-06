"""Reception views — quick check-in, walk-in, check-out, search."""

from decimal import Decimal

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)

from guesthouse.forms.bookings import WalkInBookingForm
from guesthouse.models import Booking, Guest
from guesthouse.services.booking_service import BookingError, BookingService
from guesthouse.views._common import (
    json_response,
    reception_or_above_required,
    render_gh,
)


# ------------------------------------------------------------------ #
# Search
# ------------------------------------------------------------------ #
@reception_or_above_required
@require_GET
def search(request):
    q = request.GET.get("q", "").strip()
    bookings = []
    guests = []
    if q:
        bookings = (
            Booking.objects.filter(
                Q(booking_reference__icontains=q)
                | Q(guest__first_name__icontains=q)
                | Q(guest__last_name__icontains=q)
                | Q(guest__phone__icontains=q)
                | Q(guest__email__icontains=q)
            )
            .select_related("guest", "room")[:25]
        )
        guests = Guest.objects.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(national_id_or_passport__icontains=q)
        )[:25]
    return render_gh(
        request,
        "guesthouse/reception/search.html",
        {"q": q, "bookings": bookings, "guests": guests, "active_nav": "checkin"},
    )


# ------------------------------------------------------------------ #
# Walk-in
# ------------------------------------------------------------------ #
@reception_or_above_required
@require_http_methods(["GET", "POST"])
def walk_in(request):
    form = WalkInBookingForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            booking, _payment = BookingService.walk_in_booking(
                first_name=form.cleaned_data["first_name"],
                last_name=form.cleaned_data["last_name"],
                phone=form.cleaned_data.get("phone", ""),
                email=form.cleaned_data.get("email", ""),
                national_id=form.cleaned_data.get("national_id", ""),
                room=form.cleaned_data["room"],
                check_in=form.cleaned_data["check_in_date"],
                check_out=form.cleaned_data["check_out_date"],
                adults=form.cleaned_data.get("adults", 1),
                children=form.cleaned_data.get("children", 0),
                special_requests=form.cleaned_data.get("special_requests", ""),
                payment_amount=form.cleaned_data.get("payment_amount") or 0,
                payment_method=form.cleaned_data.get("payment_method", "cash"),
                payment_reference=form.cleaned_data.get("payment_reference", ""),
                by_user=request.user,
            )
        except BookingError as e:
            messages.error(request, str(e))
        else:
            messages.success(
                request,
                f"Walk-in booking {booking.booking_reference} created and guest checked in.",
            )
            return redirect("guesthouse:booking_detail", pk=booking.pk)
    return render_gh(
        request,
        "guesthouse/reception/walk_in.html",
        {"form": form, "active_nav": "checkin"},
    )


# ------------------------------------------------------------------ #
# Quick check-in
# ------------------------------------------------------------------ #
@reception_or_above_required
@require_http_methods(["GET", "POST"])
def quick_check_in(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room"), pk=pk
    )
    if request.method == "POST":
        try:
            BookingService.quick_check_in(
                booking,
                by_user=request.user,
                vehicle_reg=request.POST.get("vehicle_registration", ""),
                special_requests=request.POST.get("special_requests", ""),
                key_card_no=request.POST.get("key_card_no", ""),
                id_document_seen=bool(request.POST.get("id_document_seen")),
            )
        except BookingError as e:
            messages.error(request, str(e))
        else:
            messages.success(
                request, f"Guest {booking.guest.full_name} checked in."
            )
            return redirect("guesthouse:booking_detail", pk=booking.pk)
    return render_gh(
        request,
        "guesthouse/reception/quick_check_in.html",
        {"booking": booking, "active_nav": "checkin"},
    )


# ------------------------------------------------------------------ #
# Check-out
# ------------------------------------------------------------------ #
@reception_or_above_required
@require_http_methods(["GET", "POST"])
def quick_check_out(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room"), pk=pk
    )
    if request.method == "POST":
        extra = request.POST.get("extra_charges") or 0
        try:
            BookingService.quick_check_out(
                booking,
                by_user=request.user,
                extra_charges=Decimal(str(extra)) if extra else 0,
                departure_notes=request.POST.get("departure_notes", ""),
            )
        except BookingError as e:
            messages.error(request, str(e))
        else:
            messages.success(
                request, f"Guest {booking.guest.full_name} checked out."
            )
            return redirect("guesthouse:checkout_invoice_pdf", pk=booking.pk)
    return render_gh(
        request,
        "guesthouse/reception/quick_check_out.html",
        {"booking": booking, "active_nav": "checkin"},
    )


# ------------------------------------------------------------------ #
# AJAX: find bookings pending check-in for a date
# ------------------------------------------------------------------ #
@reception_or_above_required
@require_GET
def ajax_today_arrivals(request):
    today = timezone.localdate()
    arrivals = (
        Booking.objects.filter(check_in_date=today)
        .exclude(
            booking_status__in=[
                Booking.STATUS_CANCELLED,
                Booking.STATUS_NO_SHOW,
            ]
        )
        .select_related("guest", "room")
        .order_by("booking_reference")
    )
    return json_response(
        {
            "arrivals": [
                {
                    "id": b.id,
                    "reference": b.booking_reference,
                    "guest": b.guest.full_name,
                    "room": b.room.room_number,
                    "status": b.get_booking_status_display(),
                    "adults": b.adults,
                    "children": b.children,
                }
                for b in arrivals
            ]
        }
    )
