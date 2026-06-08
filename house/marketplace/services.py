from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils.text import slugify

from marketplace.models import OwnerProfile, Property, PropertyReview


User = get_user_model()


KNOWN_LOCATION_HINTS = [
    "Maseru",
    "Masianokeng",
    "Mazenod",
    "Roma",
    "Mafeteng",
    "Leribe",
    "Berea",
    "Teyateyaneng",
    "Mohale's Hoek",
    "Qacha's Nek",
    "Butha-Buthe",
    "Thaba-Tseka",
]


def _split_location(address: str) -> tuple[str, str, str]:
    address = (address or "").strip()
    if not address:
        return "", "", ""
    lower = address.lower()
    found = [hint for hint in KNOWN_LOCATION_HINTS if hint.lower() in lower]
    city = found[0] if found else ""
    district = city or ("Maseru" if "maseru" in lower else "")
    village = ""
    return city, district, village


def _capacity_from_house_size(size: str) -> int:
    size = (size or "").lower()
    if "studio" in size:
        return 2
    for bedrooms, cap in (("1", 2), ("2", 4), ("3", 6), ("4", 8)):
        if bedrooms in size:
            return cap
    return 2


def _bedrooms_from_house_size(size: str) -> int:
    size = (size or "").lower()
    if "studio" in size:
        return 0
    for bedrooms in (4, 3, 2, 1):
        if str(bedrooms) in size:
            return bedrooms
    return 1


def _room_location_defaults() -> tuple[str, str, str]:
    return "Maseru", "Maseru", ""


def sync_owner_profile(user: User, *, bio: str = "", response_rate: int = 85):
    profile, _ = OwnerProfile.objects.get_or_create(
        user=user,
        defaults={
            "bio": bio or f"Verified owner on Property Empire.",
            "response_rate": response_rate,
        },
    )
    changed = False
    if bio and not profile.bio:
        profile.bio = bio
        changed = True
    if profile.response_rate == 0:
        profile.response_rate = response_rate
        changed = True
    if changed:
        profile.save(update_fields=["bio", "response_rate", "updated_at"])
    return profile


def _apply_source_data(prop: Property, source_obj):
    if prop.source_type == Property.SOURCE_HOUSE:
        building = source_obj.flat_building
        prop.title = f"{building.building_name} - House {source_obj.house_number}"
        prop.property_type = source_obj.house_size or "Rental House"
        prop.description = source_obj.house_size or source_obj.__str__()
        prop.location_text = building.address or ""
        prop.city, prop.district, prop.village = _split_location(building.address)
        prop.price_from = source_obj.house_rent_amount or Decimal("0.00")
        prop.guest_capacity = _capacity_from_house_size(source_obj.house_size)
        prop.bedrooms = _bedrooms_from_house_size(source_obj.house_size)
        prop.bathrooms = 1
        prop.wifi = True
        prop.parking = True
        prop.source_label = building.building_name
        prop.owner_profile = sync_owner_profile(
            source_obj.user,
            bio=f"Owner of {building.building_name} and trusted Property Empire partner.",
            response_rate=85,
        ) if source_obj.user_id else prop.owner_profile
        if getattr(source_obj, "image", None):
            prop.cover_image = source_obj.image
        prop.key_amenities = [item for item in [
            "WiFi",
            "Parking",
            "Self-catering",
        ]]
    else:
        prop.title = source_obj.room_name or f"{source_obj.room_type.name} {source_obj.room_number}"
        prop.property_type = source_obj.room_type.name if source_obj.room_type_id else "Guest House Room"
        prop.description = source_obj.description or source_obj.room_type.description or ""
        prop.location_text = source_obj.floor or source_obj.room_type.name or "Maseru"
        prop.city, prop.district, prop.village = _room_location_defaults()
        prop.price_from = source_obj.base_price_per_night or Decimal("0.00")
        prop.guest_capacity = source_obj.capacity or (source_obj.room_type.default_capacity if source_obj.room_type_id else 2)
        prop.bedrooms = 1
        prop.bathrooms = 1
        amenity_text = f"{source_obj.amenities or ''}".lower()
        prop.wifi = "wifi" in amenity_text or "wi-fi" in amenity_text or "internet" in amenity_text
        prop.parking = "park" in amenity_text or "garage" in amenity_text
        prop.air_conditioning = "air conditioning" in amenity_text or "ac" in amenity_text
        prop.swimming_pool = "pool" in amenity_text
        if getattr(source_obj, "image", None):
            prop.cover_image = source_obj.image
        prop.source_label = source_obj.room_type.name if source_obj.room_type_id else source_obj.room_number
        prop.key_amenities = [item for item in [
            *([a.strip() for a in (source_obj.amenities or "").split(",") if a.strip()]),
            "Breakfast",
            "Daily cleaning",
        ]]

    prop.slug = slugify(f"{prop.title}-{prop.source_type}-{source_obj.pk}")[:220]
    prop.save()
    return prop


@transaction.atomic
def sync_property_from_house(house):
    ct = ContentType.objects.get_for_model(house.__class__)
    prop = Property.objects.filter(
        source_content_type=ct, source_object_id=house.pk
    ).first() or Property(
        source_content_type=ct,
        source_object_id=house.pk,
        source_type=Property.SOURCE_HOUSE,
    )
    prop.source_content_type = ct
    prop.source_object_id = house.pk
    prop.source_type = Property.SOURCE_HOUSE
    return _apply_source_data(prop, house)


@transaction.atomic
def sync_property_from_room(room):
    ct = ContentType.objects.get_for_model(room.__class__)
    prop = Property.objects.filter(
        source_content_type=ct, source_object_id=room.pk
    ).first() or Property(
        source_content_type=ct,
        source_object_id=room.pk,
        source_type=Property.SOURCE_ROOM,
    )
    prop.source_content_type = ct
    prop.source_object_id = room.pk
    prop.source_type = Property.SOURCE_ROOM
    return _apply_source_data(prop, room)


@transaction.atomic
def delete_property_for_source(source_model, pk: int):
    ct = ContentType.objects.get_for_model(source_model)
    Property.objects.filter(source_content_type=ct, source_object_id=pk).delete()


def recalculate_property_stats(prop: Property):
    stats = prop.reviews.filter(is_public=True).aggregate(
        avg=Avg("rating"), count=Count("id")
    )
    prop.rating_average = Decimal(str(stats["avg"] or 0)).quantize(Decimal("0.01"))
    prop.reviews_count = stats["count"] or 0
    prop.save(update_fields=["rating_average", "reviews_count", "updated_at"])


def search_properties(queryset, params):
    q = (params.get("q") or "").strip()
    location = (params.get("location") or "").strip()
    city = (params.get("city") or "").strip()
    district = (params.get("district") or "").strip()
    village = (params.get("village") or "").strip()
    property_name = (params.get("property_name") or "").strip()
    guest_house_name = (params.get("guest_house_name") or "").strip()
    property_type = (params.get("property_type") or "").strip()
    price_min = params.get("price_min") or ""
    price_max = params.get("price_max") or ""
    bedrooms = params.get("bedrooms") or ""
    bathrooms = params.get("bathrooms") or ""
    guests = params.get("guests") or ""

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(location_text__icontains=q)
            | Q(city__icontains=q)
            | Q(district__icontains=q)
            | Q(village__icontains=q)
            | Q(source_label__icontains=q)
            | Q(property_type__icontains=q)
        )
    if location:
        queryset = queryset.filter(
            Q(location_text__icontains=location)
            | Q(city__icontains=location)
            | Q(district__icontains=location)
            | Q(village__icontains=location)
        )
    if city:
        queryset = queryset.filter(city__icontains=city)
    if district:
        queryset = queryset.filter(district__icontains=district)
    if village:
        queryset = queryset.filter(village__icontains=village)
    if property_name:
        queryset = queryset.filter(title__icontains=property_name)
    if guest_house_name:
        queryset = queryset.filter(
            Q(title__icontains=guest_house_name)
            | Q(source_label__icontains=guest_house_name)
            | Q(property_type__icontains=guest_house_name)
        )
    if property_type:
        queryset = queryset.filter(property_type__icontains=property_type)
    if price_min:
        queryset = queryset.filter(price_from__gte=price_min)
    if price_max:
        queryset = queryset.filter(price_from__lte=price_max)
    if bedrooms:
        queryset = queryset.filter(bedrooms__gte=bedrooms)
    if bathrooms:
        queryset = queryset.filter(bathrooms__gte=bathrooms)
    if guests:
        queryset = queryset.filter(guest_capacity__gte=guests)

    if params.get("wifi"):
        queryset = queryset.filter(wifi=True)
    if params.get("parking"):
        queryset = queryset.filter(parking=True)
    if params.get("swimming_pool"):
        queryset = queryset.filter(swimming_pool=True)
    if params.get("air_conditioning"):
        queryset = queryset.filter(air_conditioning=True)

    if params.get("featured"):
        queryset = queryset.filter(featured=True)
    if params.get("marketplace_enabled"):
        queryset = queryset.filter(marketplace_enabled=True)
    return queryset
