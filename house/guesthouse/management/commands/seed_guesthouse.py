"""Management command to seed the Guest House role groups & sample data."""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from guesthouse.models import Room, RoomType
from guesthouse.views._common import (
    ROLE_ADMIN,
    ROLE_HOUSEKEEPER,
    ROLE_MAINTENANCE,
    ROLE_PROPERTY_MANAGER,
    ROLE_RECEPTIONIST,
)


class Command(BaseCommand):
    help = "Create the guest house role groups and seed default room types."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-sample-rooms",
            action="store_true",
            help="Also create a few sample rooms for development.",
        )

    def handle(self, *args, **options):
        groups = [
            ROLE_ADMIN,
            ROLE_PROPERTY_MANAGER,
            ROLE_RECEPTIONIST,
            ROLE_HOUSEKEEPER,
            ROLE_MAINTENANCE,
        ]
        for name in groups:
            obj, created = Group.objects.get_or_create(name=name)
            status = "created" if created else "exists"
            self.stdout.write(f"Group '{name}' {status}.")

        sample_types = [
            ("Standard", 2, 350),
            ("Deluxe", 2, 550),
            ("Executive", 2, 850),
            ("Family Room", 4, 750),
            ("Suite", 4, 1200),
        ]
        for name, capacity, price in sample_types:
            rt, _ = RoomType.objects.get_or_create(
                name=name,
                defaults={
                    "default_capacity": capacity,
                    "default_price": price,
                },
            )
            self.stdout.write(f"Room type '{rt.name}' ready.")

        if options["with_sample_rooms"]:
            sample = [
                ("101", 1, "Standard"),
                ("102", 1, "Standard"),
                ("201", 2, "Deluxe"),
                ("202", 2, "Deluxe"),
                ("301", 3, "Executive"),
                ("401", 4, "Suite"),
            ]
            for number, floor, type_name in sample:
                rt = RoomType.objects.get(name=type_name)
                room, created = Room.objects.get_or_create(
                    room_number=number,
                    defaults={
                        "room_name": f"Room {number}",
                        "room_type": rt,
                        "floor": str(floor),
                        "capacity": rt.default_capacity,
                        "base_price_per_night": rt.default_price,
                    },
                )
                status = "created" if created else "exists"
                self.stdout.write(f"Room {room.room_number} {status}.")

        self.stdout.write(self.style.SUCCESS("Guest house seed completed."))
