from django.db import models
from django.contrib.auth.models import User
# Create your models here.


class Queue(models.Model):
    file = models.FileField(upload_to="uploads/")
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Queue {self.pk} - Processed: {self.processed}"
