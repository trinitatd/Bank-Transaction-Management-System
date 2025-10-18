from django.core.management.base import BaseCommand
from django.db import connection, transaction
from bank.models import Customer

class Command(BaseCommand):
    help = 'Process entries in customer_sync_queue and create bank.Customer rows for legacy customers'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, aadhaar_no FROM customer_sync_queue WHERE processed=0 ORDER BY created_at LIMIT 200")
            rows = cursor.fetchall()
            if not rows:
                self.stdout.write('No rows to process')
                return
            for rid, aad in rows:
                try:
                    cursor.execute("SELECT name, phone FROM customer WHERE aadhaar_no=%s LIMIT 1", [aad])
                    crow = cursor.fetchone()
                    name = crow[0] if crow and crow[0] else f'Customer {aad}'
                    phone = crow[1] if crow and crow[1] else ''
                except Exception:
                    name = f'Customer {aad}'
                    phone = ''
                # create Customer if not exists
                if not Customer.objects.filter(aadhaar_no=aad).exists():
                    Customer.objects.create(aadhaar_no=aad, name=name, phone=phone)
                    self.stdout.write(f'Created Customer {aad} - {name}')
                else:
                    self.stdout.write(f'Customer {aad} already exists')
                # mark processed
                cursor.execute("UPDATE customer_sync_queue SET processed=1, processed_at=NOW() WHERE id=%s", [rid])
        self.stdout.write('Processing complete')
