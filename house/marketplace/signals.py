from __future__ import annotations

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from guesthouse.models import Room, RoomType
from tennants.models import FlatBuilding, House

from .services import delete_property_for_source, sync_property_from_house, sync_property_from_room


@receiver(post_save, sender=House)
def house_saved(sender, instance, **kwargs):
    sync_property_from_house(instance)


@receiver(post_delete, sender=House)
def house_deleted(sender, instance, **kwargs):
    delete_property_for_source(House, instance.pk)


@receiver(post_save, sender=FlatBuilding)
def building_saved(sender, instance, **kwargs):
    for house in instance.houses.select_related("flat_building", "user"):
        sync_property_from_house(house)


@receiver(post_save, sender=Room)
def room_saved(sender, instance, **kwargs):
    sync_property_from_room(instance)


@receiver(post_delete, sender=Room)
def room_deleted(sender, instance, **kwargs):
    delete_property_for_source(Room, instance.pk)


@receiver(post_save, sender=RoomType)
def room_type_saved(sender, instance, **kwargs):
    for room in instance.rooms.select_related("room_type"):
        sync_property_from_room(room)

