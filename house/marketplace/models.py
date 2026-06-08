from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone
from django.utils.text import slugify


User = get_user_model()


class OwnerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="marketplace_owner_profile"
    )
    bio = models.TextField(blank=True)
    profile_photo = models.ImageField(
        upload_to="marketplace/owners/", blank=True, null=True
    )
    response_rate = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__first_name", "user__last_name", "user__username")

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def total_listings(self):
        return self.listings.filter(marketplace_enabled=True).count()

    @property
    def average_rating(self):
        stats = self.listings.filter(marketplace_enabled=True).aggregate(
            avg=Avg("rating_average")
        )
        return stats["avg"] or Decimal("0.00")


class Property(models.Model):
    SOURCE_HOUSE = "house"
    SOURCE_ROOM = "room"
    SOURCE_CHOICES = (
        (SOURCE_HOUSE, "Rental House"),
        (SOURCE_ROOM, "Guest House Room"),
    )

    source_content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="marketplace_properties"
    )
    source_object_id = models.PositiveIntegerField(db_index=True)
    source_object = GenericForeignKey("source_content_type", "source_object_id")
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    source_label = models.CharField(max_length=180, blank=True)

    owner_profile = models.ForeignKey(
        OwnerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
    )

    title = models.CharField(max_length=180, db_index=True)
    property_type = models.CharField(max_length=120, db_index=True)
    description = models.TextField(blank=True)
    location_text = models.CharField(max_length=255, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True, db_index=True)
    village = models.CharField(max_length=120, blank=True, db_index=True)

    slug = models.SlugField(max_length=220, unique=True, blank=True, db_index=True)
    marketplace_enabled = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, db_index=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True, db_index=True
    )

    cover_image = models.ImageField(
        upload_to="marketplace/properties/", blank=True, null=True
    )
    price_from = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating_average = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, db_index=True
    )
    reviews_count = models.PositiveIntegerField(default=0, db_index=True)

    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    guest_capacity = models.PositiveSmallIntegerField(default=1, db_index=True)
    wifi = models.BooleanField(default=False, db_index=True)
    parking = models.BooleanField(default=False, db_index=True)
    swimming_pool = models.BooleanField(default=False, db_index=True)
    air_conditioning = models.BooleanField(default=False, db_index=True)
    key_amenities = models.JSONField(default=list, blank=True)

    listed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-featured", "-listed_at")
        constraints = [
            models.UniqueConstraint(
                fields=("source_type", "source_object_id"),
                name="unique_marketplace_source_object",
            )
        ]
        indexes = [
            models.Index(fields=["marketplace_enabled", "featured"]),
            models.Index(fields=["city", "district", "village"]),
            models.Index(fields=["price_from", "guest_capacity"]),
        ]

    def clean(self):
        if self.price_from is not None and self.price_from < 0:
            raise ValidationError({"price_from": "Price must be non-negative."})
        if self.guest_capacity is not None and self.guest_capacity < 1:
            raise ValidationError({"guest_capacity": "Guest capacity must be at least 1."})

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.title or self.source_label or f"property-{self.source_object_id}"
            self.slug = slugify(base)[:200]
        if not self.source_label:
            self.source_label = self.title
        self.full_clean(exclude=["source_object"])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def gallery_images(self):
        # Include marketplace PropertyImage gallery
        images = list(self.images.all().order_by("sort_order", "id"))
        # Also include source object gallery images (HouseImage / RoomImage)
        source_obj = self.source_object
        if source_obj:
            source_images = getattr(source_obj, "images", None)
            if source_images is not None:
                for img in source_images.all().order_by("sort_order", "id"):
                    # Create a compatible wrapper so templates can use .image.url
                    images.append(img)
        return images

    @property
    def amenity_list(self):
        return [item for item in self.key_amenities if item]

    @property
    def main_image(self):
        if self.cover_image:
            return self.cover_image
        # Check source object's image field first (House.image or Room.image)
        source_image = getattr(self.source_object, "image", None)
        if source_image:
            return source_image
        # Check gallery images (marketplace PropertyImage + source HouseImage/RoomImage)
        gallery = self.gallery_images
        if gallery:
            first = gallery[0]
            return first.image
        return None

    @property
    def is_bookable(self):
        return self.marketplace_enabled and self.source_type == self.SOURCE_ROOM

    @property
    def location_summary(self):
        parts = [self.village, self.city, self.district]
        return ", ".join([p for p in parts if p]) or self.location_text or "Lesotho"

    @property
    def review_summary(self):
        return f"{self.rating_average:.1f} ({self.reviews_count} reviews)"


class PropertyImage(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="marketplace/properties/gallery/")
    caption = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def clean(self):
        if self.property_id and self.property.images.exclude(pk=self.pk).count() >= 10:
            raise ValidationError("A property may have at most 10 gallery images.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.caption or f"Image for {self.property}"


class PropertyReview(models.Model):
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer_name = models.CharField(max_length=120)
    reviewer_email = models.EmailField(blank=True)
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160, blank=True)
    body = models.TextField(blank=True)
    is_public = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["property", "is_public"])]

    def clean(self):
        if not (1 <= int(self.rating or 0) <= 5):
            raise ValidationError({"rating": "Rating must be between 1 and 5."})
        if not self.reviewer_name.strip():
            raise ValidationError({"reviewer_name": "Reviewer name is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self.recalculate_property()

    def delete(self, *args, **kwargs):
        prop = self.property
        super().delete(*args, **kwargs)
        self.recalculate_property(prop)

    def recalculate_property(self, prop=None):
        prop = prop or self.property
        stats = prop.reviews.filter(is_public=True).aggregate(
            avg=Avg("rating"), count=Count("id")
        )
        prop.rating_average = Decimal(str(stats["avg"] or 0)).quantize(Decimal("0.01"))
        prop.reviews_count = stats["count"] or 0
        prop.save(update_fields=["rating_average", "reviews_count", "updated_at"])


class PropertyInquiry(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONTACTED = "contacted"
    STATUS_CONVERTED = "converted"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_CONVERTED, "Converted"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name="inquiries"
    )
    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests = models.PositiveSmallIntegerField(default=1)
    message = models.TextField(blank=True)
    source_booking_reference = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def clean(self):
        if self.check_in and self.check_out and self.check_out <= self.check_in:
            raise ValidationError({"check_out": "Check-out must be after check-in."})
        if self.guests < 1:
            raise ValidationError({"guests": "At least one guest is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - {self.property.title}"
