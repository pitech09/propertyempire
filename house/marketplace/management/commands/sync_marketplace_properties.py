from django.core.management.base import BaseCommand

from guesthouse.models import Room
from marketplace.services import sync_property_from_house, sync_property_from_room
from tennants.models import House


class Command(BaseCommand):
    help = "Mirror houses and guesthouse rooms into the public marketplace layer."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Rebuild marketplace listings from scratch.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            from marketplace.models import Property

            Property.objects.all().delete()
            self.stdout.write(self.style.WARNING("Existing marketplace listings cleared."))

        house_count = 0
        room_count = 0
        for house in House.objects.select_related("flat_building", "user"):
            sync_property_from_house(house)
            house_count += 1
        for room in Room.objects.select_related("room_type"):
            sync_property_from_room(room)
            room_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Marketplace sync complete. houses={house_count} rooms={room_count}"
            )
        )

