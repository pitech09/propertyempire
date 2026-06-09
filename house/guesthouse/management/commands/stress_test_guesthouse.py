"""Stress-test data for the Guest House platform.

Generates room types, rooms, guests, bookings (past/current/future),
stays, payments, housekeeping tasks, and room maintenance issues in
one go so the dashboard, calendar, search, and reports screens have
plenty to chew on.

Usage:
    python manage.py stress_test_guesthouse                # default counts
    python manage.py stress_test_guesthouse --reset        # wipe & recreate
    python manage.py stress_test_guesthouse --rooms 40 --bookings 200
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from guesthouse.models import (
    Booking,
    Guest,
    GuestPayment,
    Room,
    RoomMaintenance,
    RoomType,
)
from guesthouse.services.booking_service import BookingError, BookingService
from guesthouse.views._common import (
    ROLE_ADMIN,
    ROLE_HOUSEKEEPER,
    ROLE_MAINTENANCE,
    ROLE_PROPERTY_MANAGER,
    ROLE_RECEPTIONIST,
)

User = get_user_model()


FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph",
    "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy",
    "Daniel", "Lisa", "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Dorothy", "Paul", "Kimberly", "Andrew",
    "Emily", "Joshua", "Donna", "Kenneth", "Michelle", "Kevin", "Carol",
    "Brian", "Amanda", "George", "Melissa", "Edward", "Deborah",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson",
    "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee",
    "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez",
    "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
    "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker",
    "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts",
]

NATIONALITIES = [
    "Lesotho", "South Africa", "Botswana", "Zimbabwe", "Namibia", "Eswatini",
    "Zambia", "Mozambique", "Tanzania", "Kenya", "Uganda", "Ghana", "Nigeria",
    "United Kingdom", "United States", "Germany", "France", "Netherlands",
    "India", "China", "Australia", "Brazil",
]

SPECIAL_REQUESTS = [
    "", "", "",
    "Late check-in around 11pm",
    "High floor please",
    "Quiet room away from elevator",
    "Extra pillows and blankets",
    "Vegetarian breakfast options",
    "Airport pickup needed",
    "Twin beds if possible",
    "Honeymoon - would love a room upgrade if available",
    "Travelling with infant - need a cot",
    "Allergic to feather pillows",
    "Working desk with good lighting",
]

MAINTENANCE_TITLES = [
    "Air conditioner not cooling",
    "Hot water takes too long",
    "TV remote missing batteries",
    "Bathroom drain slow",
    "Door handle loose",
    "Window blind stuck",
    "Light bulb burned out",
    "Safe battery low",
    "Wi-Fi signal weak in room",
    "Mini bar not cooling",
    "Carpet stain needs cleaning",
    "Toilet seat loose",
]

def _rand_phone() -> str:
    return f"+{random.choice([266, 27, 267, 268])}5{random.randint(1000000, 9999999)}"[:13]


def _rand_money(low: int, high: int) -> Decimal:
    return Decimal(random.randint(low, high)).quantize(Decimal("0.01"))


def _rand_date_within(days_back: int, days_forward: int) -> date:
    today = timezone.now().date()
    delta = random.randint(-days_back, days_forward)
    return today + timedelta(days=delta)


class Command(BaseCommand):
    help = "Generate a large volume of realistic data for the guest house platform."

    def add_arguments(self, parser):
        parser.add_argument("--room-types", type=int, default=8)
        parser.add_argument("--rooms-per-type", type=int, default=6)
        parser.add_argument("--guests", type=int, default=120)
        parser.add_argument("--bookings", type=int, default=180)
        parser.add_argument("--maintenance-issues", type=int, default=25)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing guesthouse data before seeding (DANGEROUS).",
        )
        parser.add_argument(
            "--skip-availability",
            action="store_true",
            default=True,
            help="Allow bookings on the same room/dates (default: True for stress tests).",
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self.stdout.write(self.style.MIGRATE_HEADING("Guest House stress test"))
        self.stdout.write(
            f"  room_types={options['room_types']} rooms/type={options['rooms_per_type']} "
            f"guests={options['guests']} bookings={options['bookings']}"
        )

        self._ensure_groups()
        staff = self._make_staff_users()
        room_types = self._make_room_types(options["room_types"])
        rooms = self._make_rooms(room_types, options["rooms_per_type"])
        guests = self._make_guests(options["guests"])
        self._make_bookings(
            rooms,
            guests,
            options["bookings"],
            staff,
            skip_availability=options["skip_availability"],
        )
        self._make_maintenance_issues(rooms, staff, options["maintenance_issues"])

        self._print_summary()
        self.stdout.write(self.style.SUCCESS("Guest house stress-test data ready."))

    # ------------------------------------------------------------------ #
    def _reset(self):
        self.stdout.write(self.style.WARNING("Resetting guesthouse tables..."))
        GuestPayment.objects.all().delete()
        Booking.objects.all().delete()
        RoomMaintenance.objects.all().delete()
        Guest.objects.all().delete()
        Room.objects.all().delete()
        RoomType.objects.all().delete()

    # ------------------------------------------------------------------ #
    def _ensure_groups(self):
        for name in (
            ROLE_ADMIN,
            ROLE_PROPERTY_MANAGER,
            ROLE_RECEPTIONIST,
            ROLE_HOUSEKEEPER,
            ROLE_MAINTENANCE,
        ):
            Group.objects.get_or_create(name=name)

    def _make_staff_users(self):
        staff = {}
        roles = {
            "admin": (ROLE_ADMIN, True, True),
            "manager": (ROLE_PROPERTY_MANAGER, True, False),
            "reception1": (ROLE_RECEPTIONIST, False, False),
            "reception2": (ROLE_RECEPTIONIST, False, False),
            "housekeeper1": (ROLE_HOUSEKEEPER, False, False),
            "housekeeper2": (ROLE_HOUSEKEEPER, False, False),
            "maint1": (ROLE_MAINTENANCE, False, False),
        }
        for username, (role, is_staff, is_super) in roles.items():
            user, created = User.objects.get_or_create(
                username=f"gh_{username}",
                defaults={
                    "email": f"gh_{username}@example.com",
                    "first_name": username.title(),
                    "last_name": "Demo",
                    "is_staff": is_staff,
                    "is_superuser": is_super,
                },
            )
            if created:
                user.set_password("TestPass123!")
                user.save(update_fields=["password"])
            user.groups.add(Group.objects.get(name=role))
            staff[username] = user
        self.stdout.write(f"  + {len(staff)} staff users")
        return staff

    # ------------------------------------------------------------------ #
    def _make_room_types(self, count: int):
        presets = [
            ("Standard Single", 1, 280, "bi-door-closed"),
            ("Standard Double", 2, 380, "bi-door-open"),
            ("Deluxe Twin", 2, 480, "bi-hospital"),
            ("Deluxe Double", 2, 520, "bi-stars"),
            ("Executive King", 2, 750, "bi-gem"),
            ("Junior Suite", 3, 950, "bi-house-door"),
            ("Family Room", 4, 850, "bi-people"),
            ("Presidential Suite", 4, 1800, "bi-trophy"),
        ]
        types = []
        for name, cap, price, icon in presets[:count]:
            rt, _ = RoomType.objects.get_or_create(
                name=name,
                defaults={
                    "default_capacity": cap,
                    "default_price": price,
                    "icon": icon,
                    "description": f"{name} — comfortable accommodation for up to {cap} guests.",
                    "is_active": True,
                },
            )
            types.append(rt)
        self.stdout.write(f"  + {len(types)} room types")
        return types

    def _make_rooms(self, room_types, per_type: int):
        rooms = []
        floors = ["1", "2", "3", "4", "5"]
        for rt in room_types:
            for i in range(per_type):
                room_number = f"{rt.id:02d}{i + 1:02d}"
                r, _ = Room.objects.get_or_create(
                    room_number=room_number,
                    defaults={
                        "room_name": f"{rt.name} {room_number}",
                        "room_type": rt,
                        "floor": random.choice(floors),
                        "capacity": rt.default_capacity,
                        "base_price_per_night": rt.default_price,
                        "weekend_price": (rt.default_price * Decimal("1.20")).quantize(Decimal("0.01")),
                        "amenities": "Wi-Fi, TV, Air conditioning, Mini bar, Safe",
                        "status": random.choice(
                            [
                                Room.STATUS_AVAILABLE,
                                Room.STATUS_AVAILABLE,
                                Room.STATUS_AVAILABLE,
                                Room.STATUS_CLEANING,
                                Room.STATUS_MAINTENANCE,
                            ]
                        ),
                        "active": True,
                    },
                )
                rooms.append(r)
        self.stdout.write(f"  + {len(rooms)} rooms")
        return rooms

    def _make_guests(self, count: int):
        guests = []
        for i in range(1, count + 1):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}{i:04d}@example.com"
            phone = _rand_phone()
            g, _ = Guest.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": phone,
                    "national_id_or_passport": f"P{random.randint(1000000, 9999999)}",
                    "nationality": random.choice(NATIONALITIES),
                    "is_vip": random.random() < 0.1,
                    "marketing_opt_in": random.random() < 0.4,
                    "address": (
                        f"{random.randint(1, 999)} Independence Ave, "
                        f"{random.choice(['Maseru', 'Johannesburg', 'Gaborone'])}"
                    ),
                },
            )
            guests.append(g)
        self.stdout.write(f"  + {len(guests)} guests")
        return guests

    # ------------------------------------------------------------------ #
    def _make_bookings(self, rooms, guests, count: int, staff, *, skip_availability: bool):
        created = 0
        skipped = 0
        statuses_distribution = (
            ("checked_out", 0.55),
            ("checked_in", 0.10),
            ("confirmed", 0.18),
            ("pending", 0.10),
            ("cancelled", 0.05),
            ("no_show", 0.02),
        )

        def _pick_status() -> str:
            r = random.random()
            cum = 0.0
            for s, p in statuses_distribution:
                cum += p
                if r <= cum:
                    return s
            return "confirmed"

        sources = [
            Booking.SOURCE_WALK_IN,
            Booking.SOURCE_PHONE,
            Booking.SOURCE_WEBSITE,
            Booking.SOURCE_BOOKING_COM,
            Booking.SOURCE_AIRBNB,
            Booking.SOURCE_AGENT,
        ]
        staff_user = staff.get("reception1") or staff.get("admin")

        for _ in range(count):
            guest = random.choice(guests)
            room = random.choice(rooms)
            status = _pick_status()

            if status == "checked_out":
                check_in = _rand_date_within(120, 30)
            elif status in ("checked_in", "confirmed", "no_show"):
                check_in = _rand_date_within(2, 7)
            elif status == "cancelled":
                check_in = _rand_date_within(30, 30)
            else:
                check_in = _rand_date_within(0, 90)

            nights = random.choices(
                [1, 2, 3, 4, 5, 7, 14],
                weights=[5, 15, 25, 20, 15, 10, 10],
            )[0]
            check_out = check_in + timedelta(days=nights)
            if check_out <= check_in:
                check_out = check_in + timedelta(days=1)

            adults = random.choices(
                [1, 2, 2, 2, 3, 4],
                weights=[10, 40, 20, 20, 5, 5],
            )[0]
            children = random.choices(
                [0, 0, 0, 0, 1, 2],
                weights=[60, 10, 10, 5, 10, 5],
            )[0]

            initial_status = (
                Booking.STATUS_CONFIRMED
                if status not in ("pending", "cancelled", "no_show")
                else (
                    Booking.STATUS_PENDING
                    if status == "pending"
                    else (
                        Booking.STATUS_CANCELLED
                        if status == "cancelled"
                        else Booking.STATUS_NO_SHOW
                    )
                )
            )

            try:
                with transaction.atomic():
                    booking = BookingService.create_booking(
                        guest=guest,
                        room=room,
                        check_in=check_in,
                        check_out=check_out,
                        adults=min(adults, room.capacity),
                        children=min(children, max(0, room.capacity - adults)),
                        booking_source=random.choice(sources),
                        discount=Decimal("0"),
                        special_requests=random.choice(SPECIAL_REQUESTS),
                        by_user=staff_user,
                        status=initial_status,
                        skip_availability_check=skip_availability,
                    )
            except (BookingError, Exception) as e:
                skipped += 1
                continue

            # Walk through lifecycle
            try:
                if status in ("checked_in", "checked_out"):
                    BookingService.quick_check_in(
                        booking,
                        by_user=staff_user,
                        vehicle_reg=(
                            f"{random.choice(['A', 'B', 'C', 'D'])} "
                            f"{random.randint(100, 999)} GP"
                        ),
                        key_card_no=f"K-{random.randint(100, 999)}",
                        id_document_seen=True,
                        special_requests=booking.special_requests,
                    )

                if status == "checked_out":
                    stay = booking.stay
                    stay.actual_check_out = stay.actual_check_in + timedelta(
                        days=nights, hours=random.randint(-3, 5)
                    )
                    stay.departure_notes = random.choice(
                        ["", "", "", "All good", "Late checkout requested", "Extra towels used"]
                    )
                    stay.save()
                    booking.actual_check_out = stay.actual_check_out
                    booking.booking_status = Booking.STATUS_CHECKED_OUT
                    booking.save(
                        update_fields=["actual_check_out", "booking_status", "updated_at"]
                    )
                    room.status = random.choice(
                        [Room.STATUS_CLEANING, Room.STATUS_AVAILABLE]
                    )
                    room.save(update_fields=["status", "updated_at"])

                    pay_method = random.choice(
                        [
                            GuestPayment.METHOD_CASH,
                            GuestPayment.METHOD_CARD,
                            GuestPayment.METHOD_EFT,
                            GuestPayment.METHOD_MOBILE_MONEY,
                        ]
                    )
                    amount = booking.total_amount
                    if random.random() < 0.15:
                        amount = (amount * Decimal(random.uniform(0.3, 0.9))).quantize(Decimal("0.01"))
                    GuestPayment.objects.create(
                        booking=booking,
                        amount=amount,
                        payment_method=pay_method,
                        reference_number=(
                            f"REF-{random.randint(10000, 99999)}"
                            if pay_method != GuestPayment.METHOD_CASH
                            else ""
                        ),
                        received_by=staff_user,
                    )
                elif status == "checked_in":
                    room.status = Room.STATUS_OCCUPIED
                    room.save(update_fields=["status", "updated_at"])
                elif status == "cancelled":
                    pass  # already set in initial_status
                elif status == "no_show":
                    pass  # already set in initial_status
            except Exception:
                skipped += 1
                continue

            created += 1

        self.stdout.write(f"  + {created} bookings ({skipped} skipped)")

    # ------------------------------------------------------------------ #
    def _make_maintenance_issues(self, rooms, staff, count: int):
        maint_user = staff.get("maint1") or staff.get("admin")
        statuses = ["open", "open", "in_progress", "resolved", "closed"]
        priorities = ["low", "medium", "medium", "high", "urgent"]
        for _ in range(count):
            room = random.choice(rooms)
            title = random.choice(MAINTENANCE_TITLES)
            status = random.choice(statuses)
            RoomMaintenance.objects.get_or_create(
                room=room,
                title=title,
                defaults={
                    "issue": f"{title} in {room.room_number}. Reported during stress test.",
                    "priority": random.choice(priorities),
                    "status": status,
                    "reported_by": maint_user,
                    "assigned_to": maint_user if random.random() < 0.4 else None,
                    "reported_date": timezone.now() - timedelta(days=random.randint(0, 30)),
                    "resolved_date": timezone.now() if status == "resolved" else None,
                    "resolution_notes": "Fixed during maintenance round." if status == "resolved" else "",
                    "cost": _rand_money(50, 2000) if status in ("resolved", "closed") else None,
                },
            )
        self.stdout.write(f"  + {count} maintenance issues")

    # ------------------------------------------------------------------ #
    def _print_summary(self):
        counts = {
            "Room Types": RoomType.objects.count(),
            "Rooms": Room.objects.count(),
            "Guests": Guest.objects.count(),
            "Bookings": Booking.objects.count(),
            "Checked In": Booking.objects.filter(booking_status=Booking.STATUS_CHECKED_IN).count(),
            "Checked Out": Booking.objects.filter(booking_status=Booking.STATUS_CHECKED_OUT).count(),
            "Stays": Booking.objects.filter(stay__isnull=False).count(),
            "Payments": GuestPayment.objects.count(),
            "Maintenance": RoomMaintenance.objects.count(),
        }
        self.stdout.write(self.style.MIGRATE_HEADING("Summary"))
        for label, count in counts.items():
            self.stdout.write(f"  {label}: {count}")
