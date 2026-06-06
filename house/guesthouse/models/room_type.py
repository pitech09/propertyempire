"""RoomType model for the Guest House module.

A RoomType describes the *category* of a rentable room
(Standard, Deluxe, Suite, etc.) and provides the defaults
that new Rooms can inherit.
"""

from django.db import models
from django.utils.text import slugify


class RoomType(models.Model):
    """Category / class of guest rooms."""

    name = models.CharField(max_length=80, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, blank=True, db_index=True)
    description = models.TextField(blank=True)
    default_capacity = models.PositiveSmallIntegerField(
        default=2,
        help_text="How many guests this room type usually accommodates.",
    )
    default_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Default nightly rate for this room type.",
    )
    icon = models.CharField(
        max_length=40,
        blank=True,
        help_text="Optional icon class (Bootstrap-icons / Material).",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Room Type"
        verbose_name_plural = "Room Types"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def room_count(self):
        return self.rooms.filter(active=True).count()
