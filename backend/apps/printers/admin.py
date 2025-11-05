from django.contrib import admin

from .models import PrinterArrangements, Printers

# Register your models here.


@admin.register(Printers)
class PrintersAdmin(admin.ModelAdmin):
    pass


@admin.register(PrinterArrangements)
class PrinterArrangementsAdmin(admin.ModelAdmin):
    pass
