from datetime import timedelta
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from tennants.models import SMSRetryMessage
from tennants.services.sms import TwilioNotificationService


class Command(BaseCommand):
    help = "Retry failed SMS messages that are due for another attempt."

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Keep running and check for due failed SMS messages repeatedly.",
        )
        parser.add_argument(
            "--sleep",
            type=int,
            default=60,
            help="Seconds to sleep between checks when --watch is used.",
        )

    def handle(self, *args, **options):
        if options["watch"]:
            while True:
                self._retry_due_messages()
                time.sleep(options["sleep"])
        else:
            self._retry_due_messages()

    def _retry_due_messages(self):
        due_messages = SMSRetryMessage.objects.filter(
            status="pending",
            next_attempt_at__lte=timezone.now(),
            attempts__lt=F("max_attempts"),
        ).order_by("next_attempt_at", "created_at")

        retry_interval = getattr(settings, "SMS_RETRY_INTERVAL_MINUTES", 6)
        service = TwilioNotificationService()
        retried = 0
        sent = 0
        failed = 0

        for queued_sms in due_messages:
            with transaction.atomic():
                queued_sms = SMSRetryMessage.objects.select_for_update().get(pk=queued_sms.pk)
                if (
                    queued_sms.status != "pending"
                    or queued_sms.next_attempt_at > timezone.now()
                    or queued_sms.attempts >= queued_sms.max_attempts
                ):
                    continue

                retried += 1
                success, result = service.send_sms(
                    queued_sms.to_number,
                    queued_sms.message,
                    queue_on_failure=False,
                )
                queued_sms.attempts += 1
                queued_sms.last_error = "" if success else str(result)
                queued_sms.external_id = str(result) if success else queued_sms.external_id

                if success:
                    queued_sms.status = "sent"
                    sent += 1
                elif queued_sms.attempts >= queued_sms.max_attempts:
                    queued_sms.status = "failed"
                    failed += 1
                else:
                    queued_sms.next_attempt_at = timezone.now() + timedelta(minutes=retry_interval)

                queued_sms.save(
                    update_fields=[
                        "attempts",
                        "last_error",
                        "external_id",
                        "status",
                        "next_attempt_at",
                        "updated_at",
                    ]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"SMS retry complete. Retried: {retried}. Sent: {sent}. Failed permanently: {failed}."
            )
        )
