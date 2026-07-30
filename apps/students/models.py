from django.db import models
from django.conf import settings

class Student(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        null=True,
        blank=True,
    )

    student_id = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=255
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    faculty = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    course = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    year = models.IntegerField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name