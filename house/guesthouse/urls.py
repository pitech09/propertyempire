"""URL config for the guesthouse app (mounted under /guesthouse/)."""

from django.urls import path

from guesthouse.views import (
    ajax,
    bookings,
    dashboard,
    guests,
    housekeeping,
    invoices,
    maintenance,
    payments,
    reception,
    reports,
    room_types,
    rooms,
)
from guesthouse.views.logout import logout_view

app_name = "guesthouse"

urlpatterns = [
    # ----- Dashboard -----
    path("", dashboard.dashboard, name="dashboard"),

    # ----- Logout -----
    path("logout/", logout_view, name="logout"),

    # ----- Rooms -----
    path("rooms/", rooms.room_list, name="room_list"),
    path("rooms/add/", rooms.room_create, name="room_create"),
    path("rooms/<int:pk>/", rooms.room_detail, name="room_detail"),
    path("rooms/<int:pk>/edit/", rooms.room_edit, name="room_edit"),
    path("rooms/<int:pk>/delete/", rooms.room_delete, name="room_delete"),
    path("rooms/<int:pk>/images/", rooms.room_images, name="room_images"),
    path("rooms/<int:pk>/images/<int:image_pk>/delete/", rooms.room_image_delete, name="room_image_delete"),

    # ----- Room Types -----
    path("room-types/", room_types.room_type_list, name="room_type_list"),
    path("room-types/add/", room_types.room_type_create, name="room_type_create"),
    path(
        "room-types/<int:pk>/edit/",
        room_types.room_type_edit,
        name="room_type_edit",
    ),
    path(
        "room-types/<int:pk>/delete/",
        room_types.room_type_delete,
        name="room_type_delete",
    ),

    # ----- Guests -----
    path("guests/", guests.guest_list, name="guest_list"),
    path("guests/add/", guests.guest_create, name="guest_create"),
    path("guests/<int:pk>/", guests.guest_detail, name="guest_detail"),
    path("guests/<int:pk>/edit/", guests.guest_edit, name="guest_edit"),
    path("guests/<int:pk>/delete/", guests.guest_delete, name="guest_delete"),

    # ----- Bookings -----
    path("bookings/", bookings.booking_list, name="booking_list"),
    path("bookings/add/", bookings.booking_create, name="booking_create"),
    path("bookings/<int:pk>/", bookings.booking_detail, name="booking_detail"),
    path("bookings/<int:pk>/edit/", bookings.booking_edit, name="booking_edit"),
    path("bookings/<int:pk>/delete/", bookings.booking_delete, name="booking_delete"),
    path("bookings/<int:pk>/cancel/", bookings.booking_cancel, name="booking_cancel"),
    path("bookings/<int:pk>/confirm/", bookings.booking_confirm, name="booking_confirm"),

    # ----- Calendar -----
    path("calendar/", bookings.calendar_view, name="calendar"),
    path("calendar/events/", bookings.calendar_events, name="calendar_events"),

    # ----- Reception -----
    path("reception/", reception.search, name="reception_search"),
    path("reception/walk-in/", reception.walk_in, name="walk_in"),
    path(
        "reception/quick-check-in/<int:pk>/",
        reception.quick_check_in,
        name="quick_check_in",
    ),
    path(
        "reception/quick-check-out/<int:pk>/",
        reception.quick_check_out,
        name="quick_check_out",
    ),
    path("reception/arrivals/", reception.ajax_today_arrivals, name="ajax_arrivals"),

    # ----- Payments -----
    path("payments/", payments.payment_list, name="payment_list"),
    path(
        "payments/new/<int:booking_pk>/",
        payments.payment_create_for_booking,
        name="payment_create",
    ),
    path("payments/<int:pk>/", payments.payment_detail, name="payment_detail"),
    path(
        "payments/<int:pk>/receipt/",
        payments.payment_receipt_pdf,
        name="payment_receipt_pdf",
    ),

    # ----- Invoices / PDFs -----
    path(
        "bookings/<int:pk>/invoice/",
        invoices.booking_invoice_pdf,
        name="booking_invoice_pdf",
    ),
    path(
        "bookings/<int:pk>/checkout-invoice/",
        invoices.checkout_invoice_pdf,
        name="checkout_invoice_pdf",
    ),

    # ----- Housekeeping -----
    path("housekeeping/", housekeeping.task_list, name="task_list"),
    path("housekeeping/add/", housekeeping.task_create, name="task_create"),
    path("housekeeping/<int:pk>/edit/", housekeeping.task_edit, name="task_edit"),
    path("housekeeping/<int:pk>/complete/", housekeeping.task_complete, name="task_complete"),
    path("housekeeping/<int:pk>/delete/", housekeeping.task_delete, name="task_delete"),

    # ----- Maintenance -----
    path("maintenance/", maintenance.maintenance_list, name="maintenance_list"),
    path("maintenance/add/", maintenance.maintenance_create, name="maintenance_create"),
    path("maintenance/<int:pk>/edit/", maintenance.maintenance_edit, name="maintenance_edit"),
    path("maintenance/<int:pk>/delete/", maintenance.maintenance_delete, name="maintenance_delete"),

    # ----- Reports -----
    path("reports/", reports.report_index, name="report_index"),
    path("reports/occupancy/", reports.occupancy_report, name="report_occupancy"),
    path("reports/revenue/", reports.revenue_report, name="report_revenue"),
    path("reports/bookings/", reports.booking_report, name="report_bookings"),
    path("reports/guests/", reports.guest_history_report, name="report_guests"),

    # ----- AJAX helpers -----
    path("ajax/availability/", rooms.ajax_check_availability, name="ajax_availability"),
    path("ajax/room/<int:pk>/pricing/", rooms.ajax_room_pricing, name="ajax_room_pricing"),
    path("ajax/dashboard/", ajax.ajax_dashboard_metrics, name="ajax_dashboard"),
    path("ajax/rooms/occupancy/", ajax.ajax_rooms_occupancy, name="ajax_rooms_occupancy"),
    path(
        "ajax/booking/<int:pk>/status/",
        ajax.ajax_booking_quick_status,
        name="ajax_booking_status",
    ),
]
