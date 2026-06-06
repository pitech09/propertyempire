"""Guest CRUD views."""

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

from guesthouse.forms.guests import GuestForm
from guesthouse.models import Booking, Guest, GuestPayment
from guesthouse.views._common import (
    admin_or_manager_required,
    reception_or_above_required,
    render_gh,
    role_required,
)


@role_required()
@require_http_methods(["GET"])
def guest_list(request):
    q = request.GET.get("q", "").strip()
    guests = Guest.objects.all()
    if q:
        guests = guests.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(email__icontains=q)
            | Q(national_id_or_passport__icontains=q)
        )
    guests = guests.annotate(
        bookings_count=Count("bookings", distinct=True),
    ).order_by("-bookings_count", "last_name", "first_name")
    return render_gh(
        request,
        "guesthouse/guests/guest_list.html",
        {"guests": guests, "q": q, "active_nav": "guests"},
    )


@reception_or_above_required
@require_http_methods(["GET", "POST"])
def guest_create(request):
    form = GuestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        g = form.save()
        messages.success(request, f"Guest {g.full_name} created.")
        return redirect("guesthouse:guest_detail", pk=g.pk)
    return render_gh(
        request,
        "guesthouse/guests/guest_form.html",
        {"form": form, "active_nav": "guests"},
    )


@role_required()
@require_http_methods(["GET"])
def guest_detail(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    bookings = guest.bookings.select_related("room").order_by("-check_in_date")[:30]
    total_spent = GuestPayment.objects.filter(
        booking__guest=guest
    ).aggregate(total=Sum("amount"))["total"] or 0
    return render_gh(
        request,
        "guesthouse/guests/guest_detail.html",
        {
            "guest": guest,
            "bookings": bookings,
            "total_spent": total_spent,
            "active_nav": "guests",
        },
    )


@reception_or_above_required
@require_http_methods(["GET", "POST"])
def guest_edit(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    form = GuestForm(request.POST or None, instance=guest)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Guest updated.")
        return redirect("guesthouse:guest_detail", pk=guest.pk)
    return render_gh(
        request,
        "guesthouse/guests/guest_form.html",
        {"form": form, "guest": guest, "active_nav": "guests"},
    )


@admin_or_manager_required
@require_POST
def guest_delete(request, pk):
    guest = get_object_or_404(Guest, pk=pk)
    if guest.bookings.exists():
        messages.error(
            request, "Cannot delete a guest with existing bookings."
        )
    else:
        guest.delete()
        messages.success(request, "Guest deleted.")
    return redirect("guesthouse:guest_list")
