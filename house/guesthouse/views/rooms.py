"""Room & RoomType CRUD views."""

import datetime as _dt
import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone as _tz
from django.views.decorators.http import require_http_methods, require_POST

from guesthouse.forms.images import GuestHouseImageForm
from guesthouse.forms.rooms import RoomForm, RoomImageForm, RoomTypeForm
from guesthouse.models import Booking, GuestHouseImage, Room, RoomImage, RoomType
from guesthouse.services.availability import BookingAvailabilityService
from guesthouse.services.pricing import PricingService
from guesthouse.views._common import (
    admin_or_manager_required,
    json_response,
    render_gh,
    role_required,
)


# ------------------------------------------------------------------ #
# RoomType
# ------------------------------------------------------------------ #
@role_required()
@require_http_methods(["GET"])
def room_type_list(request):
    types = RoomType.objects.all().order_by("name")
    return render_gh(
        request,
        "guesthouse/rooms/room_type_list.html",
        {"types": types, "active_nav": "room_types"},
    )


@admin_or_manager_required
@require_http_methods(["GET", "POST"])
def room_type_create(request):
    form = RoomTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        rt = form.save()
        messages.success(request, f"Room type '{rt.name}' created.")
        return redirect("guesthouse:room_type_list")
    return render_gh(
        request,
        "guesthouse/rooms/room_type_form.html",
        {"form": form, "active_nav": "room_types"},
    )


@admin_or_manager_required
@require_http_methods(["GET", "POST"])
def room_type_edit(request, pk):
    rt = get_object_or_404(RoomType, pk=pk)
    form = RoomTypeForm(request.POST or None, instance=rt)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room type updated.")
        return redirect("guesthouse:room_type_list")
    return render_gh(
        request,
        "guesthouse/rooms/room_type_form.html",
        {"form": form, "room_type": rt, "active_nav": "room_types"},
    )


@admin_or_manager_required
@require_POST
def room_type_delete(request, pk):
    rt = get_object_or_404(RoomType, pk=pk)
    if rt.rooms.exists():
        messages.error(
            request,
            "Cannot delete a room type that has rooms. Re-assign or remove its rooms first.",
        )
    else:
        rt.delete()
        messages.success(request, "Room type deleted.")
    return redirect("guesthouse:room_type_list")


# ------------------------------------------------------------------ #
# Room
# ------------------------------------------------------------------ #
@role_required()
@require_http_methods(["GET"])
def room_list(request):
    status_filter = request.GET.get("status", "")
    type_filter = request.GET.get("type", "")
    rooms = Room.objects.select_related("room_type").all()
    if status_filter:
        rooms = rooms.filter(status=status_filter)
    if type_filter:
        rooms = rooms.filter(room_type_id=type_filter)
    return render_gh(
        request,
        "guesthouse/rooms/room_list.html",
        {
            "rooms": rooms,
            "room_types": RoomType.objects.filter(is_active=True),
            "status_choices": Room.STATUS_CHOICES,
            "status_filter": status_filter,
            "type_filter": type_filter,
            "active_nav": "rooms",
        },
    )


@role_required()
@require_http_methods(["GET"])
def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    upcoming = (
        room.bookings.filter(check_out_date__gte=_tz.localdate())
        .exclude(booking_status=Booking.STATUS_CANCELLED)
        .order_by("check_in_date")[:10]
    )
    past = (
        room.bookings.filter(check_out_date__lt=_tz.localdate())
        .order_by("-check_in_date")[:10]
    )
    return render_gh(
        request,
        "guesthouse/rooms/room_detail.html",
        {
            "room": room,
            "upcoming_bookings": upcoming,
            "past_bookings": past,
            "active_nav": "rooms",
        },
    )


@admin_or_manager_required
@require_http_methods(["GET", "POST"])
def room_create(request):
    form = RoomForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        room = form.save()
        messages.success(request, f"Room {room.room_number} created.")
        return redirect("guesthouse:room_detail", pk=room.pk)
    return render_gh(
        request,
        "guesthouse/rooms/room_form.html",
        {"form": form, "active_nav": "rooms"},
    )


@admin_or_manager_required
@require_http_methods(["GET", "POST"])
def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RoomForm(request.POST or None, request.FILES or None, instance=room)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room updated.")
        return redirect("guesthouse:room_detail", pk=room.pk)
    return render_gh(
        request,
        "guesthouse/rooms/room_form.html",
        {"form": form, "room": room, "active_nav": "rooms"},
    )


@admin_or_manager_required
@require_POST
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    room.delete()
    messages.success(request, "Room deleted.")
    return redirect("guesthouse:room_list")


# ------------------------------------------------------------------ #
# AJAX: availability & pricing
# ------------------------------------------------------------------ #
@role_required()
@require_http_methods(["GET"])
def ajax_check_availability(request):
    """Returns JSON of available rooms for the given dates."""
    try:
        check_in = _dt.date.fromisoformat(request.GET.get("check_in", ""))
        check_out = _dt.date.fromisoformat(request.GET.get("check_out", ""))
    except (ValueError, TypeError):
        return json_response(
            {"error": "Invalid dates. Use YYYY-MM-DD."}, status=400
        )
    guests = int(request.GET.get("guests", 1) or 1)
    room_type_id = request.GET.get("room_type") or None
    if room_type_id:
        try:
            room_type_id = int(room_type_id)
        except (TypeError, ValueError):
            room_type_id = None

    rooms = BookingAvailabilityService.find_available_rooms(
        check_in, check_out, guests=guests, room_type_id=room_type_id
    )
    return json_response(
        {
            "rooms": [
                {
                    "id": r.id,
                    "room_number": r.room_number,
                    "room_name": r.room_name,
                    "room_type": r.room_type.name,
                    "capacity": r.capacity,
                    "base_price": str(r.base_price_per_night),
                    "weekend_price": str(r.weekend_price) if r.weekend_price else None,
                }
                for r in rooms
            ]
        }
    )


@role_required()
@require_http_methods(["GET"])
def ajax_room_pricing(request, pk):
    room = get_object_or_404(Room, pk=pk)
    try:
        check_in = _dt.date.fromisoformat(request.GET.get("check_in", ""))
        check_out = _dt.date.fromisoformat(request.GET.get("check_out", ""))
    except (ValueError, TypeError):
        return json_response({"error": "Invalid dates"}, status=400)
    bd = PricingService.breakdown(room, check_in, check_out)
    return json_response(bd.as_dict())


# ------------------------------------------------------------------ #
# Room Images (up to 5 pictures per room)
# ------------------------------------------------------------------ #
@role_required()
def room_images(request, pk):
    """View and manage images for a guest house room (up to 5 pictures)."""
    room = get_object_or_404(Room, pk=pk)
    images = room.images.all().order_by("sort_order", "id")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            if images.count() >= RoomImage.MAX_IMAGES:
                messages.error(request, f"Maximum of {RoomImage.MAX_IMAGES} images allowed.")
                return redirect("guesthouse:room_images", pk=room.pk)

            form = RoomImageForm(room=room, data=request.POST, files=request.FILES)
            if form.is_valid():
                room_image = form.save(commit=False)
                room_image.room = room
                room_image.save()
                messages.success(request, "Image uploaded successfully!")
                return redirect("guesthouse:room_images", pk=room.pk)
            else:
                for error in form.errors.values():
                    messages.error(request, error.as_text())

        elif action == "delete":
            image_id = request.POST.get("image_id")
            if image_id:
                img = get_object_or_404(RoomImage, pk=image_id, room=room)
                img.delete()
                messages.success(request, "Image deleted.")

        return redirect("guesthouse:room_images", pk=room.pk)

    form = RoomImageForm(room=room)
    context = {
        "room": room,
        "images": images,
        "form": form,
        "remaining_slots": RoomImage.MAX_IMAGES - images.count(),
    }
    return render_gh(request, "guesthouse/rooms/room_images.html", context)


@role_required()
def room_image_delete(request, pk, image_pk):
    """Delete a specific room image."""
    room = get_object_or_404(Room, pk=pk)
    img = get_object_or_404(RoomImage, pk=image_pk, room=room)
    if request.method == "POST":
        img.delete()
        messages.success(request, "Image deleted successfully!")
    return redirect("guesthouse:room_images", pk=room.pk)


# ------------------------------------------------------------------ #
# Guest House Property Images (up to 5 overall property pictures)
# ------------------------------------------------------------------ #
@role_required()
def guesthouse_images(request):
    """View and manage overall guest house property images (up to 5 pictures)."""
    images = GuestHouseImage.objects.all().order_by("sort_order", "id")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add":
            if images.count() >= GuestHouseImage.MAX_IMAGES:
                messages.error(
                    request, f"Maximum of {GuestHouseImage.MAX_IMAGES} images allowed."
                )
                return redirect("guesthouse:guesthouse_images")

            form = GuestHouseImageForm(data=request.POST, files=request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Image uploaded successfully!")
                return redirect("guesthouse:guesthouse_images")
            else:
                for error in form.errors.values():
                    messages.error(request, error.as_text())

        elif action == "delete":
            image_id = request.POST.get("image_id")
            if image_id:
                img = get_object_or_404(GuestHouseImage, pk=image_id)
                img.delete()
                messages.success(request, "Image deleted.")

        return redirect("guesthouse:guesthouse_images")

    form = GuestHouseImageForm()
    context = {
        "images": images,
        "form": form,
        "remaining_slots": GuestHouseImage.MAX_IMAGES - images.count(),
        "active_nav": "guesthouse_images",
    }
    return render_gh(request, "guesthouse/gallery/images.html", context)


@role_required()
def guesthouse_image_delete(request, image_pk):
    """Delete a specific guest house property image."""
    img = get_object_or_404(GuestHouseImage, pk=image_pk)
    if request.method == "POST":
        img.delete()
        messages.success(request, "Image deleted successfully!")
    return redirect("guesthouse:guesthouse_images")
