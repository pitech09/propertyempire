"""InvoiceService — generate booking invoices and payment receipts.

Renders a Django template to HTML and converts to PDF using whichever
PDF backend is available (WeasyPrint > xhtml2pdf > plain HTML).
"""

from __future__ import annotations

import io
import logging
from decimal import Decimal
from typing import Optional, Tuple

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from guesthouse.models import Booking, GuestPayment

logger = logging.getLogger(__name__)


class InvoiceService:
    """High-level helpers for generating booking & payment PDFs."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    @classmethod
    def render_booking_invoice(cls, booking: Booking) -> Tuple[str, str]:
        """Return (filename, html) for a booking invoice."""
        context = {
            "booking": booking,
            "guest": booking.guest,
            "room": booking.room,
            "nights": booking.nights,
            "now": timezone.now(),
            "payments": booking.payments.all(),
            "title": f"Invoice {booking.booking_reference}",
        }
        html = render_to_string(
            "guesthouse/invoices/booking_invoice.html", context
        )
        return f"Invoice-{booking.booking_reference}.pdf", html

    @classmethod
    def render_payment_receipt(cls, payment: GuestPayment) -> Tuple[str, str]:
        """Return (filename, html) for a single payment receipt."""
        context = {
            "payment": payment,
            "booking": payment.booking,
            "guest": payment.booking.guest,
            "room": payment.booking.room,
            "now": timezone.now(),
            "title": f"Receipt {payment.reference_number or payment.id}",
        }
        html = render_to_string(
            "guesthouse/invoices/payment_receipt.html", context
        )
        return f"Receipt-{payment.booking.booking_reference}-{payment.id}.pdf", html

    @classmethod
    def render_checkout_invoice(cls, booking: Booking) -> Tuple[str, str]:
        """Return (filename, html) for the final checkout invoice."""
        context = {
            "booking": booking,
            "guest": booking.guest,
            "room": booking.room,
            "stay": getattr(booking, "stay", None),
            "payments": booking.payments.all(),
            "now": timezone.now(),
            "title": f"Check-out Invoice {booking.booking_reference}",
        }
        html = render_to_string(
            "guesthouse/invoices/checkout_invoice.html", context
        )
        return f"Checkout-{booking.booking_reference}.pdf", html

    # ------------------------------------------------------------------ #
    # PDF rendering
    # ------------------------------------------------------------------ #
    @classmethod
    def to_pdf_response(cls, filename: str, html: str) -> HttpResponse:
        """Convert HTML to a PDF HttpResponse using the best available engine."""
        # 1. WeasyPrint (best fidelity)
        try:
            from weasyprint import HTML  # type: ignore
            buffer = io.BytesIO()
            HTML(string=html, base_url=".").write_pdf(target=buffer)
            buffer.seek(0)
            response = HttpResponse(buffer.read(), content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response
        except Exception as e:  # pragma: no cover
            logger.info("WeasyPrint not available: %s", e)

        # 2. xhtml2pdf (lighter)
        try:
            from xhtml2pdf import pisa  # type: ignore
            buffer = io.BytesIO()
            result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
            if not result.err:
                response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
                response["Content-Disposition"] = f'inline; filename="{filename}"'
                return response
            logger.info("xhtml2pdf returned errors, falling back to HTML")
        except Exception as e:  # pragma: no cover
            logger.info("xhtml2pdf not available: %s", e)

        # 3. HTML fallback
        response = HttpResponse(html, content_type="text/html")
        response["Content-Disposition"] = f'inline; filename="{filename.replace(".pdf", ".html")}"'
        return response
