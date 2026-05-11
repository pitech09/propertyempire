# tennants/management/commands/create_dummy_tenants.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from tennants.models import Tenant

User = get_user_model()

class Command(BaseCommand):
    help = 'Create dummy tenant users for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of dummy tenants to create (default: 3)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='TestPass123!',
            help='Default password for tenants (default: TestPass123!)'
        )

    def handle(self, *args, **options):
        count = options['count']
        default_password = options['password']
        
        tenants_created = []
        tenants_existing = []
        
        for i in range(1, count + 1):
            username = f"tenant{i}"
            email = f"tenant{i}@example.com"
            phone = f"+2665000{i:04d}"
            id_number = f"900000{i:04d}"[-10:]
            
            with transaction.atomic():
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': f'Tenant {i}',
                        'last_name': 'Demo',
                        'is_active': True,
                    }
                )

                if user_created:
                    user.set_password(default_password)
                    user.save(update_fields=['password'])

                tenant, tenant_created = Tenant.objects.get_or_create(
                    user=user,
                    defaults={
                        'full_name': f'Tenant Demo {i}',
                        'email': email,
                        'phone': phone,
                        'id_number': id_number,
                    }
                )

            if tenant_created:
                tenants_created.append(username)
                self.stdout.write(self.style.SUCCESS(
                    f'Created tenant: {username} | Password: {default_password}'
                ))
            elif user_created:
                tenants_created.append(username)
                self.stdout.write(self.style.SUCCESS(
                    f'Created user for existing tenant profile: {username}'
                ))
            else:
                tenants_existing.append(username)
                self.stdout.write(self.style.WARNING(f'Tenant already exists: {username}'))
        
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'Created: {len(tenants_created)} tenants'))
        if tenants_created:
            self.stdout.write(f'Usernames: {", ".join(tenants_created)}')
            self.stdout.write(f'Password for all: {default_password}')
        
        if tenants_existing:
            self.stdout.write(self.style.WARNING(f'Already existed: {len(tenants_existing)} tenants'))
            self.stdout.write(f'Usernames: {", ".join(tenants_existing)}')
        
        self.stdout.write('='*50)
        
        # Show login command example
        if tenants_created:
            self.stdout.write('\nTest login with:')
            self.stdout.write(f'curl -X POST http://localhost:8000/api/token/ \\')
            self.stdout.write(f'  -H "Content-Type: application/json" \\')
            self.stdout.write(f'  -d \'{{"username": "{tenants_created[0]}", "password": "{default_password}"}}\'')
