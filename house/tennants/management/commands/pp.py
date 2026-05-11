from django.core.management.base import BaseCommand
from tennants.models import Tenant

class Command(BaseCommand):
    help = 'List all tenants'

    def handle(self, *args, **options):
        tenants = Tenant.objects.select_related('user', 'house').all()
        
        if not tenants:
            self.stdout.write("No tenants found.")
            return
        
        self.stdout.write(f"\n{'ID':<4} {'Full Name':<25} {'Email':<30} {'Phone':<15} {'House':<10}")
        self.stdout.write("-" * 85)
        
        for t in tenants:
            house_num = t.house.house_number if t.house else '-'
            self.stdout.write(
                f"{t.id:<4} {t.full_name[:24]:<25} {t.email[:29]:<30} {str(t.phone):<15} {house_num:<10}"
            )
        self.stdout.write(f"\nTotal tenants: {tenants.count()}")