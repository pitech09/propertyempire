import logging

from django.conf import settings
from django.core.mail import send_mail

from tennants.services.sms import TwilioNotificationService

logger = logging.getLogger(__name__)


def _send_email_backup(subject, message, recipients):
    recipients = [recipient for recipient in recipients if recipient]
    if not recipients:
        logger.info("No email recipients for notification: %s", subject)
        return False

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error("Failed to send email backup for %s: %s", subject, exc)
        return False


def _landlord_for_tenant(tenant):
    return tenant.house.user if tenant.house else None


def _payment_request_message(payment_request):
    tenant = payment_request.tenant
    charge = payment_request.rent_charge
    house = tenant.house
    house_label = house.house_number if house else "Unassigned"
    building = tenant.building_name or "Unknown building"

    return (
        f"Payment request: {tenant.full_name}, M{payment_request.amount}, "
        f"{charge.get_month_display()} {charge.year}, house {house_label}, "
        f"{building}. Ref: {payment_request.payment_reference or '-'}."
    )


def notify_landlord_payment_request(payment_request):
    landlord = _landlord_for_tenant(payment_request.tenant)
    if landlord is None:
        logger.warning("Payment request %s has no landlord to notify", payment_request.pk)
        return

    subject = f"New payment request from {payment_request.tenant.full_name}"
    message = _payment_request_message(payment_request)

    sms_number = getattr(settings, "LANDLORD_SMS_NUMBER", None)
    if sms_number:
        TwilioNotificationService().send_sms(sms_number, message)
    else:
        logger.info("LANDLORD_SMS_NUMBER is not configured")

    whatsapp_number = getattr(settings, "LANDLORD_WHATSAPP_NUMBER", None)
    if whatsapp_number:
        TwilioNotificationService().send_whatsapp(whatsapp_number, message)
    else:
        logger.info("LANDLORD_WHATSAPP_NUMBER is not configured")

    _send_email_backup(subject, message, [landlord.email])


def _issue_report_message(issue):
    tenant = issue.tenant
    house = tenant.house
    house_label = house.house_number if house else "Unassigned"
    building = tenant.building_name or "Unknown building"

    return (
        f"Maintenance request: {tenant.full_name}, house {house_label}, "
        f"{building}. Issue: {issue.title}. {issue.description}"
    )


def notify_landlord_issue_report(issue):
    landlord = _landlord_for_tenant(issue.tenant)
    if landlord is None:
        logger.warning("Issue %s has no landlord to notify", issue.pk)
        return

    subject = f"New maintenance request from {issue.tenant.full_name}"
    message = _issue_report_message(issue)

    sms_number = getattr(settings, "LANDLORD_SMS_NUMBER", None)
    if sms_number:
        TwilioNotificationService().send_sms(sms_number, message)
    else:
        logger.info("LANDLORD_SMS_NUMBER is not configured")

    whatsapp_number = getattr(settings, "LANDLORD_WHATSAPP_NUMBER", None)
    if whatsapp_number:
        TwilioNotificationService().send_whatsapp(whatsapp_number, message)
    else:
        logger.info("LANDLORD_WHATSAPP_NUMBER is not configured")

    _send_email_backup(subject, message, [landlord.email])


def notify_tenant_issue_approved(issue):
    tenant = issue.tenant
    subject = f"Maintenance request approved: {issue.title}"
    message = (
        f"Hi {tenant.full_name}, your maintenance request '{issue.title}' "
        "was approved. Help will be sent within a week."
    )

    if tenant.phone:
        TwilioNotificationService().send_sms(tenant.phone, message)
    else:
        logger.info("Tenant %s has no phone for maintenance approval SMS", tenant.pk)

    _send_email_backup(subject, message, [tenant.email])
