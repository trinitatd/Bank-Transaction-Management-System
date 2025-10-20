from django.db import models
from django.contrib.auth.models import User

# Bank model
class Bank(models.Model):
    bank_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

# Bank Branch model
class BankBranch(models.Model):
    branch_number = models.CharField(max_length=15, primary_key=True)
    address = models.TextField()
    bank_code = models.ForeignKey(Bank, on_delete=models.CASCADE)

    def __str__(self):
        return f"Branch {self.branch_number} - {self.bank_code.name}"

# Customer model (no password field)
class Customer(models.Model):
    aadhaar_no = models.CharField(max_length=12, primary_key=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    

    # Optionally link to Django User for authentication
    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

# Account model
class Account(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    account_no = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.account_no

# Transaction model
class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=10,
        choices=[('DEPOSIT','Deposit'),('WITHDRAW','Withdraw')]
    )

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

# Loans model
class Loans(models.Model):
    loan_no = models.CharField(max_length=20, primary_key=True)
    type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    branch_number = models.ForeignKey(BankBranch, on_delete=models.RESTRICT)

    def __str__(self):
        return f"{self.loan_no} - {self.type}"

class CustomerLoans(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    loan = models.ForeignKey(Loans, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=20,
        choices=[('Primary Borrower','Primary Borrower'),
                 ('Co-borrower','Co-borrower'),
                 ('Guarantor','Guarantor')],
        default='Primary Borrower'
    )
    loan_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('customer', 'loan')

    def __str__(self):
        return f"{self.customer.name} - {self.loan.loan_no} ({self.role})"

class TransactionAudit(models.Model):
    transaction_id = models.BigIntegerField(null=True)
    account_id = models.BigIntegerField(null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    transaction_type = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transaction_audit'

    def __str__(self):
        return f"Audit {self.transaction_id} on {self.account_id} ({self.transaction_type})"

class CustomerSyncQueue(models.Model):
    aadhaar_no = models.CharField(max_length=12, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'customer_sync_queue'

    def __str__(self):
        return f"Sync {self.aadhaar_no} - {'done' if self.processed else 'pending'}"

class ReconciliationAudit(models.Model):
    account_id = models.BigIntegerField(null=True)
    old_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    new_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reconciliation_audit'

    def __str__(self):
        return f"Reconcile acc={self.account_id} {self.old_balance}->{self.new_balance}"
