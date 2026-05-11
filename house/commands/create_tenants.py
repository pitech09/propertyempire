# management/commands/create_tenant.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tennants.models import Tenant  # adjust import

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test tenant users'
    
    def handle(self, *args, **options):
        tenant_data = [
            {
                'username': 'tenant4',
                'password': 'TenantPass123!',
                'email': 'tenant4@example.com',
                'phone': '555-0901'
            },
            {
                'username': 'tenant44',
                'password': 'TenantPass456!',
                'email': 'tenant6@example.com',
                'phone': '555-0302'
            }
        ]
        
        for data in tenant_data:
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'email': data['email'],
                    'user_type': 'tenant'
                }
            )
            
            if created:
                user.set_password(data['password'])
                user.save()
                
                # Create tenant profile
                Tenant.objects.create(
                    user=user,
                    phone=data['phone']
                )
                self.stdout.write(f"Created tenant: {data['username']}")