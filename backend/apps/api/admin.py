from django.contrib import admin

# Register your models here.
from .models import Token


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    pass
