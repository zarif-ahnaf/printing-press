from django.db import models

# Create your models here.


class Printers(models.Model):
    model = models.CharField(max_length=100)
    simplex_charge = models.DecimalField(
        max_digits=10, null=True, blank=True, decimal_places=2
    )
    duplex_charge = models.DecimalField(
        max_digits=10, null=True, blank=True, decimal_places=2
    )

    def __str__(self):
        return self.model
