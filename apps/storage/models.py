from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

STORAGE_DAYS_LIMIT = 3


class StudentStorageLog(models.Model):
    """
    Tracks raw materials students put into a kitchen's storage.
    Unlike volunteers, students aren't fixed to one kitchen — they pick
    the kitchen when logging each item. Items are only allowed to sit in
    storage for STORAGE_DAYS_LIMIT days — after that they're flagged as
    expired and both the student and management get notified
    (see management command check_storage_expiry).
    """

    STATUS_CHOICES = [
        ("stored", "Stored"),
        ("removed", "Removed"),   # student took it back out in time
        ("expired", "Expired"),   # passed the 3-day limit while still "stored"
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="storage_logs",
    )

    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        related_name="student_storage_logs",
    )

    item_name = models.CharField(max_length=255)

    date_stored = models.DateField(
        default=timezone.localdate,
        help_text="The day the item was put into storage.",
    )

    proof_image = models.ImageField(
        upload_to="student_storage_proofs/",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="stored",
    )

    removed_at = models.DateTimeField(null=True, blank=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_stored", "-created_at"]

    @property
    def expiry_date(self):
        return self.date_stored + timedelta(days=STORAGE_DAYS_LIMIT)

    @property
    def days_left(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def is_past_limit(self):
        """True once the 3-day window has passed, regardless of stored status."""
        return timezone.localdate() > self.expiry_date

    def __str__(self):
        return f"{self.item_name} @ {self.kitchen.code} ({self.status})"