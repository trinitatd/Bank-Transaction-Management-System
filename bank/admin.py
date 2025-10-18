from django.contrib import admin
from .models import (
	Bank, BankBranch, Customer, Account, Transaction, Loans, CustomerLoans
)


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
	list_display = ('bank_code', 'name')


@admin.register(BankBranch)
class BankBranchAdmin(admin.ModelAdmin):
	list_display = ('branch_number', 'bank_code')


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
	list_display = ('aadhaar_no', 'name', 'phone')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
	list_display = ('account_no', 'customer', 'balance')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
	list_display = ('account', 'transaction_type', 'amount', 'date')


@admin.register(Loans)
class LoansAdmin(admin.ModelAdmin):
	list_display = ('loan_no', 'type', 'amount', 'branch_number')


@admin.register(CustomerLoans)
class CustomerLoansAdmin(admin.ModelAdmin):
	list_display = ('customer', 'loan', 'role', 'loan_date')


from .models import TransactionAudit, CustomerSyncQueue, ReconciliationAudit


@admin.register(TransactionAudit)
class TransactionAuditAdmin(admin.ModelAdmin):
	list_display = ('transaction_id', 'account_id', 'transaction_type', 'amount', 'created_at')


@admin.register(CustomerSyncQueue)
class CustomerSyncQueueAdmin(admin.ModelAdmin):
	list_display = ('aadhaar_no', 'processed', 'created_at', 'processed_at')


@admin.register(ReconciliationAudit)
class ReconciliationAuditAdmin(admin.ModelAdmin):
	list_display = ('account_id', 'old_balance', 'new_balance', 'created_at')
