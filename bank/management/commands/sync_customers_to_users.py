from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bank.models import Customer

class Command(BaseCommand):
    help = 'Create Django User accounts for every Customer if not present.\n\nUsage: manage.py sync_customers_to_users --password DEFAULTPWD'

    def add_arguments(self, parser):
        parser.add_argument('--password', type=str, help='Default password for created users', default='ChangeMe123!')
        parser.add_argument('--force', action='store_true', help='Force reset password for existing users')

    def handle(self, *args, **options):
        pwd = options['password']
        force = options['force']
        created = 0
        updated = 0
        for c in Customer.objects.all():
            username = c.name if c.name else c.aadhaar_no
            if not username:
                continue
            user, was_created = User.objects.get_or_create(username=username)
            if was_created:
                user.set_password(pwd)
                user.is_active = True
                user.save()
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created user: {username}'))
            else:
                if force:
                    user.set_password(pwd)
                    user.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f'Updated password for existing user: {username}'))
        self.stdout.write(self.style.SUCCESS(f'Done. Created: {created}, Updated: {updated}'))
