"""
Management command to expire accepted inquiries that have passed their
3-working-day payment deadline.

Run via cron or manually:
    python manage.py expire_accepted_inquiries

Recommended cron schedule: every 6 hours, or daily at midnight.
"""
from __future__ import annotations

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from marketplace.models import PropertyInquiry

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Expire accepted inquiries where the payment deadline has passed."

    def handle(self, *args, **options):
        now = timezone.now()

        expired_inquiries = PropertyInquiry.objects.filter(
            status=PropertyInquiry.STATUS_ACCEPTED,
            payment_deadline__lt=now,
        )

        count = expired_inquiries.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired inquiries found."))
            return

        self.stdout.write(f"Found {count} expired accepted inquiry(ies).")

        expired = 0
        for inquiry in expired_inquiries.iterator():
            try:
                inquiry.cancel_due_to_non_payment(commit=True)
                expired += 1
                logger.info(
                    "Inquiry %s (pk=%d) expired due to non-payment. "
                    "Deadline was %s, now set to payment_expired.",
                    inquiry, inquiry.pk, inquiry.payment_deadline,
                )
            except Exception as exc:
                logger.error(
                    "Failed to expire inquiry pk=%d: %s", inquiry.pk, exc
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully expired {expired} inquiry(ies). "
                f"Failed: {count - expired}."
            )
        )