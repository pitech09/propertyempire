from django.contrib import admin

from marketplace.models import OwnerProfile, Property, PropertyImage, PropertyInquiry, PropertyReview


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


class PropertyReviewInline(admin.TabularInline):
    model = PropertyReview
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "property_type", "source_type", "marketplace_enabled", "featured", "price_from", "rating_average", "reviews_count")
    list_filter = ("source_type", "marketplace_enabled", "featured", "city", "district")
    search_fields = ("title", "location_text", "city", "district", "village", "source_label")
    prepopulated_fields = {"slug": ("title",)}
    list_select_related = ("owner_profile",)
    inlines = [PropertyImageInline, PropertyReviewInline]


@admin.register(OwnerProfile)
class OwnerProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "response_rate", "total_listings", "average_rating")
    search_fields = ("user__username", "user__first_name", "user__last_name", "bio")
    autocomplete_fields = ("user",)


@admin.register(PropertyReview)
class PropertyReviewAdmin(admin.ModelAdmin):
    list_display = ("property", "reviewer_name", "rating", "is_public", "created_at")
    list_filter = ("rating", "is_public")
    search_fields = ("property__title", "reviewer_name", "title", "body")
    autocomplete_fields = ("property",)


@admin.register(PropertyInquiry)
class PropertyInquiryAdmin(admin.ModelAdmin):
    list_display = ("property", "full_name", "email", "guests", "status", "created_at")
    list_filter = ("status", "guests", "created_at")
    search_fields = ("property__title", "full_name", "email", "phone", "message")
    autocomplete_fields = ("property",)

