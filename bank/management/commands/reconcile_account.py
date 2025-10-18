from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Run sp_reconcile_account for a given account or for all accounts'

    def add_arguments(self, parser):
        parser.add_argument('--account', type=str, help='Account number to reconcile')
        parser.add_argument('--fix', action='store_true', help='Fix discrepancies when found')

    def handle(self, *args, **options):
        acc = options.get('account')
        fix = 1 if options.get('fix') else 0
        with connection.cursor() as cursor:
            if acc:
                cursor.callproc('sp_reconcile_account', [acc, fix])
                # fetch result
                for row in cursor.fetchall():
                    self.stdout.write(str(row))
            else:
                # run for all accounts in bank_account
                cursor.execute('SELECT account_no FROM bank_account')
                rows = cursor.fetchall()
                for r in rows:
                    account_no = r[0]
                    try:
                        cursor.callproc('sp_reconcile_account', [account_no, fix])
                        # fetch result
                        for row in cursor.fetchall():
                            self.stdout.write(str(row))
                    except Exception as e:
                        self.stdout.write(f'Error reconciling {account_no}: {e}')
        self.stdout.write('Done')
