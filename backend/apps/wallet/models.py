from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    def __str__(self):
        return f"{self.user.username}'s Wallet"

    def deposit(self, amount):
        amount = Decimal(amount)
        self.balance += amount
        self.save()

    def charge(self, amount, description=""):
        amount = Decimal(amount)
        self.balance -= amount
        self.save()


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ("deposit", "Deposit"),
        ("charge", "Charge"),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} of ${self.amount} for {self.user.username}"  # type: ignore
