from django.db import models

# Create your models here.
from student.models import Student
from item.models import Item

class Claim(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="claims")
    claimant = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="claims")
    message = models.TextField()
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Claim for {self.item.title}"