"""Seed baseline demo data for local development and smoke tests.

    python manage.py seed_demo

Creates subscription plans, categories, a verified+open vendor with services
and working hours, and a customer. Idempotent.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.accounts.models import Role
from apps.catalog.models import Service
from apps.subscriptions.models import PlanTier, SubscriptionPlan
from apps.subscriptions.services import set_vendor_plan
from apps.vendors.models import Category, Vendor, VendorStatus, VerificationStatus, WorkingHours

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data (plans, categories, a vendor, services, a customer)."

    def handle(self, *args, **options):
        # Plans
        plans = {
            PlanTier.BASIC: Decimal("0"),
            PlanTier.STANDARD: Decimal("499"),
            PlanTier.PREMIUM: Decimal("999"),
        }
        for tier, price in plans.items():
            SubscriptionPlan.objects.get_or_create(
                name=tier, defaults={"price": price, "max_services": None}
            )
        standard = SubscriptionPlan.objects.get(name=PlanTier.STANDARD)

        # Categories — two-level hierarchy (parent pillars + children).
        services_pillar, _ = Category.objects.get_or_create(
            name="Services", defaults={"slug": "services"}
        )
        for name in ["Reservations", "Tickets"]:
            Category.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
        for name in ["Barber", "Salon", "Spa"]:
            cat, _ = Category.objects.get_or_create(
                name=name, defaults={"slug": slugify(name), "parent": services_pillar}
            )
            if cat.parent_id != services_pillar.id:
                cat.parent = services_pillar
                cat.save(update_fields=["parent"])
        barber = Category.objects.get(name="Barber")

        # Vendor owner
        vendor_user, _ = User.objects.get_or_create(
            email="vendor@example.com",
            defaults={"role": Role.VENDOR, "full_name": "Demo Barber", "is_active": True},
        )
        vendor_user.set_password("VendorPass123")
        vendor_user.role = Role.VENDOR
        vendor_user.is_active = True
        vendor_user.save()

        vendor, _ = Vendor.objects.get_or_create(
            owner=vendor_user,
            defaults={
                "business_name": "Sharp Cuts",
                "category": barber,
                "address": "Bole, Addis Ababa",
                "location_lat": Decimal("9.010000"),
                "location_lng": Decimal("38.760000"),
                "status": VendorStatus.OPEN,
                "verification_status": VerificationStatus.VERIFIED,
            },
        )
        vendor.status = VendorStatus.OPEN
        vendor.verification_status = VerificationStatus.VERIFIED
        vendor.save()
        set_vendor_plan(vendor, standard)

        # Working hours: Mon–Sat 09:00–18:00
        for day in range(0, 6):
            WorkingHours.objects.update_or_create(
                vendor=vendor,
                day_of_week=day,
                defaults={"open_time": "09:00", "close_time": "18:00", "is_closed": False},
            )
        WorkingHours.objects.update_or_create(
            vendor=vendor, day_of_week=6, defaults={"is_closed": True}
        )

        # Services
        Service.objects.get_or_create(
            vendor=vendor,
            name="Haircut",
            defaults={"duration_minutes": 30, "price": Decimal("200")},
        )
        Service.objects.get_or_create(
            vendor=vendor,
            name="Haircut + Beard",
            defaults={"duration_minutes": 60, "price": Decimal("350")},
        )

        # Customer
        customer, _ = User.objects.get_or_create(
            email="customer@example.com",
            defaults={"role": Role.CUSTOMER, "full_name": "Demo Customer", "is_active": True},
        )
        customer.set_password("CustomerPass123")
        customer.is_active = True
        customer.save()

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
        self.stdout.write("Vendor login: vendor@example.com / VendorPass123")
        self.stdout.write("Customer login: customer@example.com / CustomerPass123")
