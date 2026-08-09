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
        on_delete=models.CASCADE,  # changed from SET_NULL — a kitchen login dies with its kitchen
        null=True,
        blank=True,
        related_name="users"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kitchen"],
                condition=models.Q(role="volunteer"),
                name="one_login_per_kitchen",
            )
        ]

    def __str__(self):
        return self.username