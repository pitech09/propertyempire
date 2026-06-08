"""Room model — a rentable unit in the guest house."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Room(models.Model):
    """A physical rentable room in the guest house."""

    STATUS_AVAILABLE = "available"
    STATUS_OCCUPIED = "occupied"
    STATUS_RESERVED = "reserved"
    STATUS_CLEANING = "cleaning"
    STATUS_MAINTENANCE = "maintenance"
    STATUS_OUT_OF_SERVICE = "out_of_service"

    STATUS_CHOICES = (
        (STATUS_AVAILABLE, "Available"),
        (STATUS_OCCUPIED, "Occupied"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_CLEANING, "Cleaning"),
        (STATUS_MAINTENANCE, "Maintenance"),
        (STATUS_OUT_OF_SERVICE, "Out of Service"),
    )

    room_number = models.CharField(max_length=20, unique=True, db_index=True)
    room_name = models.CharField(max_length=120, blank=True)
    slug = models.SlugField(max_length=140, blank=True, db_index=True)
    room_type = models.ForeignKey(
        "guesthouse.RoomType",
        on_delete=models.PROTECT,
        related_name="rooms",
        db_index=True,
    )
    description = models.TextField(blank=True)
    floor = models.CharField(max_length=20, blank=True)
    capacity = models.PositiveSmallIntegerField(default=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
        db_index=True,
    )

    base_price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    weekend_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional weekend rate (Fri/Sat).",
    )
    monthly_price_optional = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional monthly rate for long stays.",
    )

    image = models.ImageField(upload_to="guesthouse/rooms/", null=True, blank=True)
    amenities = models.TextField(
        blank=True,
        help_text="Comma separated list of amenities (Wi-Fi, AC, TV, ...).",
    )
    active = models.BooleanField(default=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("room_number",)
        indexes = [
            models.Index(fields=["status", "active"]),
        ]

    def clean(self):
        if self.capacity < 1:
            raise ValidationError({"capacity": "Capacity must be at least 1."})
        if self.base_price_per_night is None or self.base_price_per_night < 0:
            raise ValidationError(
                {"base_price_per_night": "Base price must be non-negative."}
            )
        if self.weekend_price is not None and self.weekend_price < 0:
            raise ValidationError({"weekend_price": "Weekend price must be non-negative."})
        if (
            self.monthly_price_optional is not None
            and self.monthly_price_optional < 0
        ):
            raise ValidationError(
                {"monthly_price_optional": "Monthly price must be non-negative."}
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.room_number}-{self.room_name}" or self.room_number)
        if not self.room_name:
            self.room_name = f"Room {self.room_number}"
        # If capacity not set, inherit from room type
        if (not self.capacity or self.capacity < 1) and self.room_type_id:
            self.capacity = self.room_type.default_capacity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.room_number} - {self.room_name or self.room_type.name}"

    @property
    def amenity_list(self):
        return [a.strip() for a in (self.amenities or "").split(",") if a.strip()]

    @property
    def display_label(self):
        return f"{self.room_number} • {self.room_type.name}"

    @property
    def is_bookable(self) -> bool:
        """Returns True when the room is in a bookable state."""
        return self.active and self.status not in (
            self.STATUS_OUT_OF_SERVICE,
            self.STATUS_MAINTENANCE,
        )

    def get_nightly_rate(self, date_obj) -> Decimal:
        """Returns the appropriate rate for the given night.

        Weekend rate (Fri/Sat) is used if defined, otherwise the base price.
        """
        if (
            self.weekend_price is not None
            and date_obj
            and date_obj.weekday() in (4, 5)  # Friday, Saturday
        ):
            return Decimal(self.weekend_price)
        return Decimal(self.base_price_per_night)


# ------------------------------
# RoomImage Model (up to 5 pictures per room)
# ------------------------------
class RoomImage(models.Model):
    MAX_IMAGES = 5
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    MAX_FILE_SIZE_MB = 5

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="guesthouse/rooms/gallery/")
    caption = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def clean(self):
        if self.room_id and self.room.images.exclude(pk=self.pk).count() >= self.MAX_IMAGES:
            raise ValidationError(f"A room may have at most {self.MAX_IMAGES} images.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.caption or f"Image for {self.room}"
