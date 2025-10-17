from django.db import models

class Customer(models.Model):
    aadhaar_no = models.CharField(max_length=12, primary_key=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return self.name

class Account(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    account_no = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return self.account_no

class Transaction(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=[('DEPOSIT','Deposit'),('WITHDRAW','Withdraw')])

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"
