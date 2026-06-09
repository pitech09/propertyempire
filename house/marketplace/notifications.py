from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from marketplace.models import OwnerProfile, PropertyInquiry

logger = logging.getLogger(__name__)


def _owner_contact_email(owner: OwnerProfile) -> str | None:
    """Return the owner's email if available."""
    return getattr(owner.user, "email", None) or None


def _owner_contact_phone(owner: OwnerProfile) -> str | None:
    """Return the owner's phone number if available."""
    return getattr(owner.user, "phone", None) or None


def send_inquiry_notification(inquiry: PropertyInquiry) -> tuple[bool, str]:
    """
    Notify the property owner about a new inquiry.
    Attempts email first, then falls back to SMS if possible.
    Returns (success, message).
    """
    prop = inquiry.property
    owner = prop.owner_profile
    if owner is None:
        logger.warning("Property %s has no owner, cannot notify about inquiry %s", prop.pk, inquiry.pk)
        return False, "Property has no owner."

    property_url = settings.BASE_URL.rstrip("/") + reverse(
        "marketplace:owner_inquiries"
    )

    context = {
        "inquiry": inquiry,
        "property": prop,
        "owner": owner,
        "property_url": property_url,
    }

    # Try email first
    to_email = _owner_contact_email(owner)
    if to_email:
        subject = f"New inquiry about {prop.title}"
        html_message = render_to_string("marketplace/emails/new_inquiry.html", context)
        text_message = (
            f"Hi {owner.display_name},\n\n"
            f"You have a new inquiry about '{prop.title}' from {inquiry.full_name}.\n\n"
            f"Email: {inquiry.email}\n"
            f"Phone: {inquiry.phone or 'Not provided'}\n"
            f"Guests: {inquiry.guests}\n"
            f"Check-in: {inquiry.check_in or 'Not specified'}\n"
            f"Check-out: {inquiry.check_out or 'Not specified'}\n"
            f"Message: {inquiry.message or 'No message'}\n\n"
            f"View all inquiries: {property_url}\n\n"
            f"Property Empire Marketplace"
        )
        try:
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info("Email notification sent to %s for inquiry %s", to_email, inquiry.pk)
            return True, "Email notification sent."
        except Exception as exc:
            logger.warning("Failed to send email to %s: %s", to_email, exc)
    else:
        logger.debug("Owner %s has no email address configured", owner.pk)

    # Try SMS as fallback
    to_phone = _owner_contact_phone(owner)
    if to_phone:
        sms_message = (
            f"New inquiry about '{prop.title}' from {inquiry.full_name}. "
            f"Email: {inquiry.email}. Phone: {inquiry.phone or 'N/A'}. "
            f"Message: {inquiry.message or 'No message'}. "
            f"View: {property_url}"
        )
        try:
            from tennants.services.sms import TwilioNotificationService

            service = TwilioNotificationService()
            success, result = service.send_sms(to_phone, sms_message, queue_on_failure=True)
            if success:
                logger.info("SMS notification sent to %s for inquiry %s", to_phone, inquiry.pk)
                return True, "SMS notification sent."
            logger.warning("SMS send failed to %s: %s", to_phone, result)
        except Exception as exc:
            logger.warning("Failed to send SMS to %s: %s", to_phone, exc)
    else:
        logger.debug("Owner %s has no phone number configured", owner.pk)

    return False, "No notification channel available for owner."