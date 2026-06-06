"""Stress-test data for the rental (tennants) platform.

Generates a large volume of realistic data so the UI, dashboards,
reports, and API endpoints can be exercised under load.

Usage:
    python manage.py stress_test_rental                # default counts
    python manage.py stress_test_rental --reset        # wipe & recreate
    python manage.py stress_test_rental --tenants 50 --buildings 6
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tennants.models import (
    Expense,
    FlatBuilding,
    House,
    Issue,
    MaintenanceBid,
    Payment,
    PaymentRequest,
    RentCharge,
    Tenant,
    Worker,
)

User = get_user_model()


FIRST_NAMES = [
    "Thabo", "Lineo", "Palesa", "Kabelo", "Mpho", "Tumelo", "Refilwe",
    "Karabo", "Lerato", "Matseliso", "Neo", "Bohlale", "Itumeleng",
    "Tshepiso", "Lebohang", "Nthabiseng", "Manko", "Mantsebo", "Sechaba",
    "Rethabile", "Tsebo", "Lihle", "Zanele", "Sipho", "Naledi", "Thandi",
    "Bongani", "Khanyi", "Mandla", "Lungile", "Muzi", "Lwando",
]

LAST_NAMES = [
    "Khumalo", "Mokoena", "Nkhabu", "Tau", "Letsie", "Phiri", "Sefako",
    "Dlamini", "Mabaso", "Ndlovu", "Sithole", "Maseko", "Zwane",
    "Malinga", "Mthembu", "Shongwe", "Mahlangu", "Motaung", "Mofokeng",
    "Rampolokeng", "Mokwena", "Maseela", "Mokgosi", "Seloane", "Mokoako",
]

WORKER_NAMES = [
    ("Mpho Plumbers", "plumbing, pipefitting, bathroom renovation"),
    ("Tau Electrical", "electrical, wiring, solar installation, fault finding"),
    ("Khoza Carpentry", "carpentry, roofing, door fitting, cabinets"),
    ("Mokoena Painting", "painting, plastering, waterproofing, tiling"),
    ("Ndlovu Welding", "welding, gate making, burglar bars, steelwork"),
    ("Letsie Gardens", "gardening, landscaping, tree felling, irrigation"),
    ("Phiri Cleaning", "cleaning, fumigation, pest control, deep cleaning"),
    ("Sefako HVAC", "hvac, refrigeration, air conditioning, gas refills"),
]

ISSUE_TITLES = [
    "Leaking kitchen sink",
    "No hot water in bathroom",
    "Power socket sparking",
    "Broken window latch",
    "Toilet running continuously",
    "Roof leaking in bedroom",
    "Front door lock jammed",
    "Ceiling light flickering",
    "Mould on bathroom ceiling",
    "Cracked floor tiles",
    "Burst garden pipe",
    "Geyser tripping electricity",
    "Pest infestation in kitchen",
    "Boundary wall collapsing",
    "Garage door not closing",
]


def _rand_phone() -> str:
    return f"+2665{random.randint(100, 999)}{random.randint(1000, 9999)}"


def _rand_money(low: int, high: int) -> Decimal:
    return Decimal(random.randint(low, high)).quantize(Decimal("0.01"))


def _rand_date_within(days_back: int, days_forward: int) -> date:
    today = timezone.now().date()
    delta = random.randint(-days_back, days_forward)
    return today + timedelta(days=delta)


class Command(BaseCommand):
    help = "Generate a large volume of realistic data for the rental platform."

    def add_arguments(self, parser):
        parser.add_argument("--landlords", type=int, default=3)
        parser.add_argument("--buildings", type=int, default=5)
        parser.add_argument("--houses-per-building", type=int, default=10)
        parser.add_argument("--tenants", type=int, default=40)
        parser.add_argument("--workers", type=int, default=10)
        parser.add_argument("--issues", type=int, default=25)
        parser.add_argument("--expenses", type=int, default=30)
        parser.add_argument("--payment-requests", type=int, default=20)
        parser.add_argument("--months-of-history", type=int, default=6)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing tenants/buildings before seeding (DANGEROUS).",
        )

    # ------------------------------------------------------------------ #
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self.stdout.write(self.style.MIGRATE_HEADING("Rental platform stress test"))
        self.stdout.write(
            f"  landlords={options['landlords']} buildings={options['buildings']} "
            f"houses/building={options['houses_per_building']} "
            f"tenants={options['tenants']} workers={options['workers']}"
        )

        landlords = self._make_landlords(options["landlords"])
        buildings = self._make_buildings(landlords, options["buildings"])
        houses = self._make_houses(buildings, options["houses_per_building"])
        tenants = self._make_tenants(houses, options["tenants"])
        self._make_rent_charges(tenants, options["months_of_history"])
        self._make_payments(tenants, options["months_of_history"])
        self._make_payment_requests(tenants, options["payment_requests"])
        workers = self._make_workers(options["workers"])
        self._make_issues_and_bids(tenants, workers, options["issues"])
        self._make_expenses(landlords, buildings, tenants, options["expenses"])

        self.stdout.write(self.style.SUCCESS("Rental stress-test data ready."))

    # ------------------------------------------------------------------ #
    def _reset(self):
        self.stdout.write(self.style.WARNING("Resetting rental tables..."))
        Payment.objects.all().delete()
        PaymentRequest.objects.all().delete()
        RentCharge.objects.all().delete()
        MaintenanceBid.objects.all().delete()
        Expense.objects.all().delete()
        Issue.objects.all().delete()
        Tenant.objects.all().delete()
        House.objects.all().delete()
        FlatBuilding.objects.all().delete()
        Worker.objects.all().delete()

    # ------------------------------------------------------------------ #
    def _make_landlords(self, count: int):
        landlords = []
        for i in range(1, count + 1):
            user, created = User.objects.get_or_create(
                username=f"landlord{i}",
                defaults={
                    "email": f"landlord{i}@example.com",
                    "first_name": f"Landlord {i}",
                    "last_name": "Demo",
                    "is_staff": True,
                },
            )
            if created:
                user.set_password("TestPass123!")
                user.save(update_fields=["password"])
            landlords.append(user)
        return landlords

    def _make_buildings(self, landlords, count: int):
        buildings = []
        prefixes = ["Sunrise", "Highveld", "Maseru", "Roma", "Pioneer", "Mafeteng",
                    "Leribe", "Teyateyaneng", "Mohale", "Qacha's Nek"]
        for i in range(count):
            owner = random.choice(landlords)
            b, _ = FlatBuilding.objects.get_or_create(
                building_name=f"{random.choice(prefixes)} Court {i + 1}",
                defaults={
                    "user": owner,
                    "address": f"{random.randint(1, 999)} Main Road, Maseru",
                    "number_of_houses": 0,  # updated after houses created
                },
            )
            buildings.append(b)
        return buildings

    def _make_houses(self, buildings, per_building: int):
        houses = []
        sizes = ["1 bedroom", "2 bedroom", "3 bedroom", "Studio", "1 bedroom with lounge"]
        for b in buildings:
            for n in range(1, per_building + 1):
                h, _ = House.objects.get_or_create(
                    flat_building=b,
                    house_number=f"{n:02d}",
                    defaults={
                        "user": b.user,
                        "house_size": random.choice(sizes),
                        "house_rent_amount": _rand_money(800, 4500),
                        "deposit_amount": _rand_money(800, 4500),
                        "occupation": False,
                    },
                )
                houses.append(h)
            b.number_of_houses = per_building
            b.save(update_fields=["number_of_houses"])
        return houses

    def _make_tenants(self, houses, count: int):
        tenants = []
        available_houses = list(houses)
        random.shuffle(available_houses)

        for i in range(1, count + 1):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            username = f"sttenant{i:04d}"
            email = f"sttenant{i:04d}@example.com"
            phone = _rand_phone()
            house = available_houses[i % len(available_houses)] if available_houses else None

            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "first_name": first,
                    "last_name": last,
                    "is_active": True,
                },
            )
            if user_created:
                user.set_password("TestPass123!")
                user.save(update_fields=["password"])

            tenant, _ = Tenant.objects.get_or_create(
                user=user,
                defaults={
                    "full_name": f"{first} {last}",
                    "email": email,
                    "phone": phone,
                    "id_number": f"{random.randint(100000000, 999999999)}"[-10:],
                    "house": house,
                    "is_active": house is not None,
                    "rent_due_date": timezone.now().date().replace(day=1),
                    "reminder_days_before": random.choice([1, 3, 5, 7]),
                },
            )
            if house:
                house.occupation = True
                house.save(update_fields=["occupation"])
            tenants.append(tenant)
        return tenants

    def _make_rent_charges(self, tenants, months_back: int):
        today = timezone.now().date()
        created = 0
        for t in tenants:
            if not t.house:
                continue
            rent = t.house.house_rent_amount
            for m in range(-1, months_back + 1):
                # Generate charges for the past N months and the current one
                year = today.year
                month = today.month - m
                while month <= 0:
                    month += 12
                    year -= 1
                _, created_rc = RentCharge.objects.get_or_create(
                    tenant=t,
                    year=year,
                    month=month,
                    defaults={"amount_due": rent},
                )
                if created_rc:
                    created += 1
        self.stdout.write(f"  + {created} rent charges")

    def _make_payments(self, tenants, months_back: int):
        today = timezone.now().date()
        created = 0
        methods = ["cash", "mobile_money", "bank_transfer", "cheque"]
        for t in tenants:
            charges = list(t.rent_charges.all())
            for charge in charges:
                # 80% of charges get a full or partial payment
                if random.random() < 0.8:
                    amount = charge.amount_due
                    if random.random() < 0.15:
                        # 15% partial payments
                        amount = (amount * Decimal(random.uniform(0.3, 0.9))).quantize(Decimal("0.01"))
                    method = random.choice(methods)
                    Payment.objects.create(
                        tenant=t,
                        rent_charge=charge,
                        amount=amount,
                        payment_method=method,
                        payment_reference=f"REF-{random.randint(10000, 99999)}" if method != "cash" else "",
                        paid_at=timezone.now() - timedelta(days=random.randint(0, 60)),
                    )
                    created += 1
        self.stdout.write(f"  + {created} payments")

    def _make_payment_requests(self, tenants, count: int):
        tenants_with_charges = [t for t in tenants if t.rent_charges.exists()]
        if not tenants_with_charges:
            return
        for _ in range(count):
            t = random.choice(tenants_with_charges)
            charge = random.choice(list(t.rent_charges.all()))
            PaymentRequest.objects.create(
                tenant=t,
                rent_charge=charge,
                amount=_rand_money(200, int(charge.amount_due)),
                payment_method=random.choice(["mobile_money", "bank_transfer", "cash"]),
                payment_reference=f"PR-{random.randint(1000, 9999)}",
                status=random.choice(["pending", "pending", "approved", "rejected"]),
            )
        self.stdout.write(f"  + {count} payment requests")

    def _make_workers(self, count: int):
        workers = []
        names = WORKER_NAMES * (count // len(WORKER_NAMES) + 1)
        for i in range(count):
            full_name, skills = names[i]
            w, _ = Worker.objects.get_or_create(
                email=f"worker{i:03d}@example.com",
                defaults={
                    "full_name": full_name,
                    "phone": _rand_phone(),
                    "id_number": f"{random.randint(100000000, 999999999)}"[-10:],
                    "skills": skills,
                    "is_active": True,
                    "is_approved": True,
                    "bio": f"{full_name} is a trusted contractor with {random.randint(2, 15)} years of experience.",
                },
            )
            workers.append(w)
        self.stdout.write(f"  + {len(workers)} workers")
        return workers

    def _make_issues_and_bids(self, tenants, workers, count: int):
        active_tenants = [t for t in tenants if t.is_active]
        if not active_tenants or not workers:
            return
        statuses = ["pending", "approved", "in_progress", "resolved"]
        for _ in range(count):
            t = random.choice(active_tenants)
            issue = Issue.objects.create(
                tenant=t,
                title=random.choice(ISSUE_TITLES),
                description=f"Reported by {t.full_name}. Needs urgent attention.",
                status=random.choice(statuses),
            )
            # 1-3 bids per issue
            for w in random.sample(workers, k=min(len(workers), random.randint(1, 3))):
                bid_status = (
                    "accepted" if issue.status in ("approved", "in_progress", "resolved") and random.random() < 0.3
                    else random.choice(["pending", "pending", "rejected", "withdrawn"])
                )
                MaintenanceBid.objects.create(
                    issue=issue,
                    worker=w,
                    amount=_rand_money(150, 4000),
                    estimated_days=random.randint(1, 14),
                    notes="We can source parts and complete within stated timeframe.",
                    status=bid_status,
                )
        self.stdout.write(f"  + {count} issues with bids")

    def _make_expenses(self, landlords, buildings, tenants, count: int):
        categories = [
            "utilities", "maintenance", "taxes", "insurance",
            "cleaning", "security", "management", "advertising", "supplies",
        ]
        for _ in range(count):
            landlord = random.choice(landlords)
            building = random.choice(buildings)
            tenant = random.choice([t for t in tenants if t.house and t.house.flat_building_id == building.id] or [None])
            category = random.choice(categories)
            Expense.objects.create(
                user=landlord,
                flat_building=building,
                house=tenant.house if tenant else None,
                tenant=tenant if random.random() < 0.25 else None,
                category=category,
                amount=_rand_money(100, 8000),
                description=f"{category.replace('_', ' ').title()} - {building.building_name}",
                vendor=random.choice(["Lesotho Electric Co.", "Water Affairs", "Local Hardware", "Security Co.", "Cleaning Co."]),
                expense_date=_rand_date_within(180, 30),
                is_recoverable=tenant is not None and random.random() < 0.4,
                is_recovered=tenant is not None and random.random() < 0.5,
            )
        self.stdout.write(f"  + {count} expenses")
