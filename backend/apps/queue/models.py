from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Queue(models.Model):
    file = models.FileField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    print_mode = models.CharField(
        max_length=20,
        choices=[
            ("single-sided", "Single Sided"),
            ("double-sided", "Double Sided"),
        ],
        default="single-sided",
    )

    page_count = models.PositiveBigIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Queue {self.pk} - Processed: {self.processed}"
