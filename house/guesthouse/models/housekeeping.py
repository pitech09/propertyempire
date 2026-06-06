"""Housekeeping tasks for rooms."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class HousekeepingTask(models.Model):
    """Cleaning / inspection task tied to a room."""

    TASK_CLEANING = "cleaning"
    TASK_DEEP_CLEANING = "deep_cleaning"
    TASK_INSPECTION = "inspection"
    TASK_LAUNDRY = "laundry"

    TASK_TYPE_CHOICES = (
        (TASK_CLEANING, "Cleaning"),
        (TASK_DEEP_CLEANING, "Deep Cleaning"),
        (TASK_INSPECTION, "Inspection"),
        (TASK_LAUNDRY, "Laundry"),
    )

    STATUS_PENDING = "pending"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"

    PRIORITY_CHOICES = (
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
    )

    room = models.ForeignKey(
        "guesthouse.Room",
        on_delete=models.CASCADE,
        related_name="housekeeping_tasks",
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="housekeeping_tasks",
    )
    task_type = models.CharField(
        max_length=20, choices=TASK_TYPE_CHOICES, default=TASK_CLEANING, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True
    )
    scheduled_date = models.DateField(default=timezone.now, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-scheduled_date", "-created_at")
        indexes = [
            models.Index(fields=["status", "scheduled_date"]),
        ]

    @property
    def is_open(self):
        return self.status in (self.STATUS_PENDING, self.STATUS_IN_PROGRESS)

    def __str__(self):
        return f"{self.get_task_type_display()} - Room {self.room.room_number} ({self.get_status_display()})"
