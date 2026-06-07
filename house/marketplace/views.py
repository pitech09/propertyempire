from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.models import User
from math import hypot

from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from guesthouse.models import Booking, Guest, Room
from guesthouse.services.booking_service import BookingError, BookingService
from marketplace.forms import MarketplaceSearchForm, PropertyReviewForm, PublicLeadForm
from marketplace.models import OwnerProfile, Property, PropertyInquiry, PropertyReview
from marketplace.services import KNOWN_LOCATION_HINTS, search_properties


def _base_queryset():
    return (
        Property.objects.filter(marketplace_enabled=True)
        .select_related("owner_profile", "owner_profile__user")
        .prefetch_related("images", "reviews")
    )


def _apply_date_availability(qs, check_in, check_out, guests):
    if not (check_in and check_out and check_out > check_in):
        return qs
    room_ids = []
    for prop in qs.filter(source_type=Property.SOURCE_ROOM).only("source_object_id"):
        room_ids.append(prop.source_object_id)
    if room_ids:
        booked_ids = set(
            Booking.objects.filter(
                room_id__in=room_ids,
                booking_status__in=[
                    Booking.STATUS_PENDING,
                    Booking.STATUS_CONFIRMED,
                    Booking.STATUS_CHECKED_IN,
                ],
                check_in_date__lt=check_out,
                check_out_date__gt=check_in,
            ).values_list("room_id", flat=True)
        )
        qs = qs.exclude(source_object_id__in=booked_ids)
    return qs.filter(Q(guest_capacity__gte=guests) | Q(source_type=Property.SOURCE_HOUSE))


def _search_context(request, featured_only=False, section=None):
    form = MarketplaceSearchForm(request.GET or None)
    qs = _base_queryset()
    if featured_only:
        qs = qs.filter(featured=True)
    if section == "guesthouses":
        qs = qs.filter(source_type=Property.SOURCE_ROOM)
    elif section == "rentals":
        qs = qs.filter(source_type=Property.SOURCE_HOUSE)
    elif section == "recent":
        qs = qs.order_by("-listed_at")
    elif section == "popular":
        qs = qs.order_by("-reviews_count", "-rating_average", "-listed_at")

    if form.is_valid():
        qs = search_properties(qs, form.cleaned_data)
        qs = _apply_date_availability(
            qs,
            form.cleaned_data.get("check_in"),
            form.cleaned_data.get("check_out"),
            form.cleaned_data.get("guests") or 1,
        )
    else:
        qs = qs.order_by("-featured", "-listed_at")

    return form, qs


def _detail_context(prop, *, review_form=None, lead_form=None):
    return {
        "property": prop,
        "gallery": prop.gallery_images[:10],
        "reviews": prop.reviews.filter(is_public=True)[:20],
        "review_form": review_form or PropertyReviewForm(),
        "lead_form": lead_form
        or PublicLeadForm(
            initial={
                "guests": 2,
                "check_in": timezone.localdate(),
                "check_out": timezone.localdate() + timezone.timedelta(days=1),
            }
        ),
        "nearby_properties": _base_queryset().exclude(pk=prop.pk).filter(
            Q(city__iexact=prop.city) | Q(district__iexact=prop.district)
        )[:6],
        "active_nav": "marketplace",
    }


@require_GET
def marketplace_home(request):
    form, results = _search_context(request)
    context = {
        "search_form": form,
        "properties": results[:24],
        "featured_guest_houses": _base_queryset().filter(
            source_type=Property.SOURCE_ROOM, featured=True
        )[:6],
        "featured_rentals": _base_queryset().filter(
            source_type=Property.SOURCE_HOUSE, featured=True
        )[:6],
        "recently_added": _base_queryset().order_by("-listed_at")[:6],
        "most_popular": _base_queryset().order_by("-reviews_count", "-rating_average")[:6],
        "location_hints": KNOWN_LOCATION_HINTS[:8],
        "active_nav": "marketplace",
    }
    if request.headers.get("HX-Request"):
        return render(request, "marketplace/partials/property_grid.html", context)
    return render(request, "marketplace/home.html", context)


@require_GET
def marketplace_search(request):
    form, results = _search_context(request)
    context = {"search_form": form, "properties": results[:48], "active_nav": "marketplace"}
    if request.headers.get("HX-Request"):
        return render(request, "marketplace/partials/property_grid.html", context)
    return render(request, "marketplace/search_results.html", context)


@require_GET
def location_suggestions(request):
    q = (request.GET.get("q") or "").strip().lower()
    suggestions = []
    if q:
        seen = set()
        for prop in _base_queryset().only("city", "district", "village", "location_text", "title", "source_label"):
            candidates = [
                prop.city,
                prop.district,
                prop.village,
                prop.location_text,
                prop.title,
                prop.source_label,
            ]
            for candidate in candidates:
                if candidate and candidate.lower().startswith(q) and candidate not in seen:
                    suggestions.append(candidate)
                    seen.add(candidate)
                    if len(suggestions) >= 8:
                        break
            if len(suggestions) >= 8:
                break
        for fallback in KNOWN_LOCATION_HINTS:
            if fallback.lower().startswith(q) and fallback not in seen:
                suggestions.append(fallback)
            if len(suggestions) >= 8:
                break
    return render(
        request,
        "marketplace/partials/location_suggestions.html",
        {"suggestions": suggestions, "query": q},
    )


@require_GET
def property_detail(request, slug):
    prop = get_object_or_404(
        _base_queryset().filter(slug=slug)
    )
    return render(request, "marketplace/properties/detail.html", _detail_context(prop))


@require_http_methods(["POST"])
def property_enquiry(request, slug):
    prop = get_object_or_404(_base_queryset().filter(slug=slug))
    form = PublicLeadForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "marketplace/properties/detail.html",
            _detail_context(prop, lead_form=form),
            status=400,
        )

    cleaned = form.cleaned_data
    if prop.source_type == Property.SOURCE_ROOM:
        full_name = cleaned["full_name"].strip()
        first_name, _, remainder = full_name.partition(" ")
        last_name = remainder or first_name
        guest, _ = Guest.objects.get_or_create(
            first_name=first_name or full_name,
            last_name=last_name or "Guest",
            phone=cleaned.get("phone") or "",
            defaults={
                "email": cleaned["email"],
                "national_id_or_passport": "",
            },
        )
        try:
            booking = BookingService.create_booking(
                guest=guest,
                room=prop.source_object,
                check_in=cleaned["check_in"],
                check_out=cleaned["check_out"],
                adults=cleaned.get("guests") or 1,
                children=0,
                booking_source=Booking.SOURCE_WEBSITE,
                special_requests=cleaned.get("message", ""),
                by_user=None,
                status=Booking.STATUS_PENDING,
            )
        except BookingError as exc:
            form.add_error(None, str(exc))
            return render(
                request,
                "marketplace/properties/detail.html",
                _detail_context(prop, lead_form=form),
                status=400,
            )
        PropertyInquiry.objects.create(
            property=prop,
            full_name=cleaned["full_name"],
            email=cleaned["email"],
            phone=cleaned.get("phone", ""),
            check_in=cleaned.get("check_in"),
            check_out=cleaned.get("check_out"),
            guests=cleaned.get("guests") or 1,
            message=cleaned.get("message", ""),
            source_booking_reference=booking.booking_reference,
            status=PropertyInquiry.STATUS_CONVERTED,
        )
        messages.success(request, f"Booking request submitted. Reference: {booking.booking_reference}")
    else:
        PropertyInquiry.objects.create(
            property=prop,
            full_name=cleaned["full_name"],
            email=cleaned["email"],
            phone=cleaned.get("phone", ""),
            check_in=cleaned.get("check_in"),
            check_out=cleaned.get("check_out"),
            guests=cleaned.get("guests") or 1,
            message=cleaned.get("message", ""),
        )
        messages.success(request, "Your enquiry has been sent to the owner.")
    return redirect("marketplace:property_detail", slug=prop.slug)


@require_http_methods(["POST"])
def property_review(request, slug):
    prop = get_object_or_404(_base_queryset().filter(slug=slug))
    form = PropertyReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.property = prop
        review.save()
        messages.success(request, "Thanks for your review.")
    else:
        messages.error(request, "Please fix the review form and try again.")
    return redirect("marketplace:property_detail", slug=prop.slug)


@require_GET
def owner_profile(request, username):
    user = get_object_or_404(User, username=username)
    profile = getattr(user, "marketplace_owner_profile", None)
    if profile is None:
        profile, _ = OwnerProfile.objects.get_or_create(user=user)
    properties = _base_queryset().filter(owner_profile=profile)
    return render(
        request,
        "marketplace/owners/detail.html",
        {
            "owner": profile,
            "properties": properties,
            "active_nav": "marketplace",
        },
    )


@require_GET
def nearby_properties(request):
    try:
        lat = Decimal(request.GET.get("lat", "0"))
        lng = Decimal(request.GET.get("lng", "0"))
    except Exception:
        lat = lng = Decimal("0")
    candidates = list(
        _base_queryset().exclude(latitude__isnull=True, longitude__isnull=True)
    )
    candidates.sort(
        key=lambda prop: (
            hypot(float((prop.latitude or 0) - lat), float((prop.longitude or 0) - lng)),
            -1 if prop.featured else 0,
            -float(prop.rating_average or 0),
        )
    )
    qs = candidates[:24]
    return render(
        request,
        "marketplace/search_results.html",
        {
            "properties": qs,
            "search_form": MarketplaceSearchForm(
                initial={"location": "", "guests": 2}
            ),
            "active_nav": "marketplace",
        },
    )
