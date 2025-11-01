from django.db import models

# Create your models here.


class Printers(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="printers/", null=True, blank=True)
    is_color = models.BooleanField(default=False)
    simplex_charge = models.DecimalField(max_digits=10, null=True, decimal_places=2)
    duplex_charge = models.DecimalField(max_digits=10, null=True, decimal_places=2)

    decomissioned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({'Color' if self.is_color else 'B&W'}) - {'Decomissioned' if self.decomissioned else 'Active'}"


class PrinterArrangements(models.Model):
    color_printer = models.ForeignKey(
        Printers,
        on_delete=models.CASCADE,
        related_name="color_printer",
        null=True,
        blank=True,
    )

    bw_printer = models.ForeignKey(
        Printers,
        on_delete=models.CASCADE,
        related_name="bw_printer",
        null=True,
        blank=True,
    )

    decomissioned = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.decomissioned:
            raise ValueError("Cannot update a decomissioned printer arrangement.")
        super().save(*args, **kwargs)

    def __str__(self):
        description = (
            "Arrangement: "
            + ("Decomissioned; " if self.decomissioned else "Active; ")
            + (
                f"Color Printer - {self.color_printer.model}; "
                if self.color_printer
                else ""
            )
            + (
                f"Black & White Printer - {self.bw_printer.model}; "
                if self.bw_printer
                else ""
            )
        )
        return description
