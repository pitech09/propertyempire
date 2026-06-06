"""PDF invoice & receipt views."""

from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from guesthouse.models import Booking
from guesthouse.services.invoice_service import InvoiceService
from guesthouse.views._common import role_required


@role_required()
@require_GET
def booking_invoice_pdf(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("guest", "room", "room__room_type"),
        pk=pk,
    )
    filename, html = InvoiceService.render_booking_invoice(booking)
    return InvoiceService.to_pdf_response(filename, html)


@role_required()
@require_GET
def checkout_invoice_pdf(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related(
            "guest", "room", "room__room_type", "stay"
        ),
        pk=pk,
    )
    filename, html = InvoiceService.render_checkout_invoice(booking)
    return InvoiceService.to_pdf_response(filename, html)
