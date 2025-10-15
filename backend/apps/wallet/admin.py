from django.contrib import admin
from .models import Wallet, Transaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance")
    search_fields = ("user__username",)
    readonly_fields = ("balance",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "transaction_type", "amount", "description", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("user__username", "description")
    readonly_fields = ("created_at",)
