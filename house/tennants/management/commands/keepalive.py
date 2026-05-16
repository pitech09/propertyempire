import time
import requests

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Keep server awake by pinging itself"

    def handle(self, *args, **kwargs):

        url = getattr(
            settings,
            "KEEPALIVE_URL",
            "http://127.0.0.1:8000/health/"
        )

        while True:
            try:
                response = requests.get(url, timeout=10)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Pinged {url} -> {response.status_code}"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(str(e))
                )

            time.sleep(60)  # safer than 5s