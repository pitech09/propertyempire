"""Signal handlers — auto-create the Guest House role groups on migrate."""

from django.apps import AppConfig
from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from guesthouse.views._common import ALL_ROLES


@receiver(post_migrate)
def create_guesthouse_groups(sender: AppConfig, **kwargs):
    """Create the five guesthouse role groups when the app is migrated."""
    if getattr(sender, "name", None) != "guesthouse":
        return
    for role in ALL_ROLES:
        Group.objects.get_or_create(name=role)
