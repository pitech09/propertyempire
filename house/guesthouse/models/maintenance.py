"""Room maintenance issues — distinct from tenant maintenance issues."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class RoomMaintenance(models.Model):
    """Maintenance / repair request against a room.

    This is separate from the long-term rental `Issue` model so that the
    two business domains (rental vs short-stay) stay clearly separated.
    """

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"

    PRIORITY_CHOICES = (
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_URGENT, "Urgent"),
    )

    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    )

    room = models.ForeignKey(
        "guesthouse.Room",
        on_delete=models.CASCADE,
        related_name="maintenance_issues",
        db_index=True,
    )
    title = models.CharField(max_length=200, db_index=True)
    issue = models.TextField()
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_maintenance_reported",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="room_maintenance_assigned",
    )
    reported_date = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_date = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-reported_date",)
        verbose_name = "Room Maintenance"
        verbose_name_plural = "Room Maintenance"
        indexes = [
            models.Index(fields=["status", "priority"]),
        ]

    def __str__(self):
        return f"{self.title} - Room {self.room.room_number} ({self.get_status_display()})"
