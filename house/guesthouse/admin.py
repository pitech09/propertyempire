"""Django admin for the Guest House module."""

from django.contrib import admin
from django.utils.html import format_html

from guesthouse.models import (
    Booking,
    Guest,
    GuestPayment,
    HousekeepingTask,
    Room,
    RoomMaintenance,
    RoomType,
    Stay,
)


# --------------------------------------------------------------------- #
@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "default_capacity", "default_price", "room_count", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


# --------------------------------------------------------------------- #
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "room_number", "room_name", "room_type", "floor", "capacity",
        "base_price_per_night", "weekend_price", "status_badge", "active",
    )
    list_filter = ("status", "active", "room_type", "floor")
    search_fields = ("room_number", "room_name", "description")
    prepopulated_fields = {"slug": ("room_name",)}
    autocomplete_fields = ()
    list_select_related = ("room_type",)

    def status_badge(self, obj):
        color = {
            Room.STATUS_AVAILABLE: "#16a34a",
            Room.STATUS_OCCUPIED: "#dc2626",
            Room.STATUS_RESERVED: "#f59e0b",
            Room.STATUS_CLEANING: "#3b82f6",
            Room.STATUS_MAINTENANCE: "#a855f7",
            Room.STATUS_OUT_OF_SERVICE: "#6b7280",
        }.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:6px;font-size:.75rem;">{}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"


# --------------------------------------------------------------------- #
@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "phone", "email", "nationality",
        "is_vip", "total_stays", "total_spent", "last_stay_at",
    )
    list_filter = ("is_vip", "nationality")
    search_fields = (
        "first_name", "last_name", "phone", "email",
        "national_id_or_passport",
    )
    readonly_fields = ("total_spent", "total_stays", "last_stay_at", "created_at", "updated_at")


# --------------------------------------------------------------------- #
class GuestPaymentInline(admin.TabularInline):
    model = GuestPayment
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("amount", "payment_method", "reference_number", "payment_date", "received_by")


class StayInline(admin.StackedInline):
    model = Stay
    extra = 0
    can_delete = False
    readonly_fields = (
        "actual_check_in", "actual_check_out",
        "created_at", "updated_at",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "booking_reference", "guest", "room", "check_in_date", "check_out_date",
        "nights", "adults", "children", "booking_source", "status_badge",
        "total_amount", "amount_paid", "balance",
    )
    list_filter = (
        "booking_status", "booking_source", "room__room_type",
        "check_in_date",
    )
    search_fields = (
        "booking_reference", "guest__first_name", "guest__last_name",
        "guest__phone", "guest__email", "room__room_number",
    )
    readonly_fields = (
        "booking_reference", "nights", "room_rate", "subtotal",
        "taxes", "total_amount", "amount_paid", "balance",
        "created_at", "updated_at", "actual_check_in", "actual_check_out",
    )
    date_hierarchy = "check_in_date"
    inlines = [StayInline, GuestPaymentInline]
    list_select_related = ("guest", "room", "room__room_type")

    def status_badge(self, obj):
        return format_html(
            '<span class="badge">{}</span>', obj.get_booking_status_display()
        )
    status_badge.short_description = "Status"

    def balance(self, obj):
        return obj.balance
    balance.short_description = "Balance"


# --------------------------------------------------------------------- #
@admin.register(Stay)
class StayAdmin(admin.ModelAdmin):
    list_display = (
        "booking", "actual_check_in", "actual_check_out",
        "adults", "children", "vehicle_registration", "is_open",
    )
    list_filter = ("id_document_seen",)
    search_fields = ("booking__booking_reference", "vehicle_registration")


# --------------------------------------------------------------------- #
@admin.register(GuestPayment)
class GuestPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "booking", "amount", "payment_method", "reference_number",
        "payment_date", "received_by",
    )
    list_filter = ("payment_method", "payment_date")
    search_fields = (
        "booking__booking_reference", "reference_number",
        "booking__guest__first_name", "booking__guest__last_name",
    )
    date_hierarchy = "payment_date"
    autocomplete_fields = ("booking",)
    list_select_related = ("booking", "booking__guest")


# --------------------------------------------------------------------- #
@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = (
        "room", "task_type", "status_badge", "priority",
        "scheduled_date", "assigned_to", "completed_date",
    )
    list_filter = ("status", "task_type", "priority")
    search_fields = ("room__room_number", "notes")
    list_select_related = ("room", "assigned_to")
    date_hierarchy = "scheduled_date"

    def status_badge(self, obj):
        return format_html(
            '<span class="badge">{}</span>', obj.get_status_display()
        )
    status_badge.short_description = "Status"


# --------------------------------------------------------------------- #
@admin.register(RoomMaintenance)
class RoomMaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "title", "room", "priority", "status_badge",
        "assigned_to", "reported_date", "resolved_date",
    )
    list_filter = ("status", "priority")
    search_fields = ("title", "issue", "resolution_notes", "room__room_number")
    list_select_related = ("room", "assigned_to", "reported_by")
    date_hierarchy = "reported_date"

    def status_badge(self, obj):
        return format_html(
            '<span class="badge">{}</span>', obj.get_status_display()
        )
    status_badge.short_description = "Status"
