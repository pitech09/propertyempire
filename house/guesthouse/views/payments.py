"""Guest payment views + PDF receipt generation."""

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from guesthouse.forms.payments import GuestPaymentForm
from guesthouse.models import Booking, GuestPayment
from guesthouse.services.invoice_service import InvoiceService
from guesthouse.views._common import (
    reception_or_above_required,
    render_gh,
    role_required,
)


@role_required()
@require_GET
def payment_list(request):
    qs = GuestPayment.objects.select_related(
        "booking", "booking__guest", "booking__room"
    )
    method = request.GET.get("method", "")
    q = request.GET.get("q", "").strip()
    if method:
        qs = qs.filter(payment_method=method)
    if q:
        qs = qs.filter(
            Q(booking__booking_reference__icontains=q)
            | Q(booking__guest__first_name__icontains=q)
            | Q(booking__guest__last_name__icontains=q)
            | Q(reference_number__icontains=q)
        )
    totals = qs.aggregate(total=Sum("amount"))
    return render_gh(
        request,
        "guesthouse/payments/payment_list.html",
        {
            "payments": qs.order_by("-payment_date")[:200],
            "method_choices": GuestPayment.METHOD_CHOICES,
            "method_filter": method,
            "q": q,
            "total_amount": totals.get("total") or 0,
            "active_nav": "payments",
        },
    )


@reception_or_above_required
@require_http_methods(["GET", "POST"])
def payment_create_for_booking(request, booking_pk):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room"), pk=booking_pk
    )
    form = GuestPaymentForm(request.POST or None, booking=booking)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False)
        payment.booking = booking
        payment.received_by = request.user
        payment.save()
        messages.success(
            request, f"Payment of {payment.amount} recorded."
        )
        return redirect("guesthouse:booking_detail", pk=booking.pk)
    return render_gh(
        request,
        "guesthouse/payments/payment_form.html",
        {"form": form, "booking": booking, "active_nav": "payments"},
    )


@role_required()
@require_GET
def payment_detail(request, pk):
    payment = get_object_or_404(
        GuestPayment.objects.select_related(
            "booking", "booking__guest", "booking__room", "received_by"
        ),
        pk=pk,
    )
    return render_gh(
        request,
        "guesthouse/payments/payment_detail.html",
        {"payment": payment, "active_nav": "payments"},
    )


@role_required()
@require_GET
def payment_receipt_pdf(request, pk):
    payment = get_object_or_404(
        GuestPayment.objects.select_related(
            "booking", "booking__guest", "booking__room"
        ),
        pk=pk,
    )
    filename, html = InvoiceService.render_payment_receipt(payment)
    return InvoiceService.to_pdf_response(filename, html)
