from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    ROLE_CHOICES = [
        ("management", "Management"),
        ("volunteer", "Volunteer"),
        ("student", "Student"),
    ]


    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )


    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )


    def __str__(self):
        return self.username