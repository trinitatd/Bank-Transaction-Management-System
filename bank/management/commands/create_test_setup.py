from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection


class Command(BaseCommand):
    help = "Create test user (testuser/TestPass123) and sample account ACC1001"

    def handle(self, *args, **options):
        username = 'testuser'
        password = 'TestPass123'
        if not User.objects.filter(username=username).exists():
            User.objects.create_user(username=username, email='test@example.com', password=password)
            self.stdout.write(self.style.SUCCESS(f'Created user: {username} / {password}'))
        else:
            self.stdout.write('Test user already exists')

        # Create sample account row if bank_account table exists
        try:
            with connection.cursor() as c:
                # ensure table exists
                c.execute("SHOW TABLES LIKE 'bank_account'")
                if not c.fetchone():
                    self.stdout.write(self.style.WARNING('Table bank_account not found. Skipping account creation.'))
                    return

                c.execute("SELECT COUNT(*) FROM bank_account WHERE account_no=%s", ['ACC1001'])
                if c.fetchone()[0] == 0:
                    c.execute(
                        "INSERT INTO bank_account (account_no, customer_id, balance, is_closed) VALUES (%s, %s, %s, 0)",
                        ('ACC1001', 'CUST1001', 1000.00)
                    )
                    self.stdout.write(self.style.SUCCESS('Created account ACC1001 with balance 1000.00'))
                else:
                    self.stdout.write('Account ACC1001 already exists')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating account: {e}'))
