"""GuestHouse image model — overall property pictures (up to 5)."""

from django.core.exceptions import ValidationError
from django.db import models


class GuestHouseImage(models.Model):
    """An image of the guest house property (exterior, lobby, common areas, etc.).

    These are global property images, not tied to a specific room.
    Limited to MAX_IMAGES per overall guest house.
    """

    MAX_IMAGES = 5
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    MAX_FILE_SIZE_MB = 5

    image = models.ImageField(upload_to="guesthouse/gallery/")
    caption = models.CharField(max_length=160, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "id")

    def clean(self):
        if self.pk is None and GuestHouseImage.objects.count() >= self.MAX_IMAGES:
            raise ValidationError(
                f"The guest house may have at most {self.MAX_IMAGES} images."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.caption or f"Guest house image #{self.pk}"

    @classmethod
    def remaining_slots(cls) -> int:
        return cls.MAX_IMAGES - cls.objects.count()