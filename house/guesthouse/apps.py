from django.apps import AppConfig


class GuesthouseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "guesthouse"
    verbose_name = "Guest House / Short-Stay"

    def ready(self):
        # Register permissions/groups on first migration
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
