from django.db import models
from django.conf import settings
from django.utils import timezone


class Kitchen(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("maintenance", "Under Maintenance"),
        ("closed", "Closed"),
    ]

    name = models.CharField(
        max_length=100
    )


    code = models.CharField(
        max_length=20,
        unique=True
    )


    location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )


    description = models.TextField(
        blank=True,
        null=True
    )


    is_active = models.BooleanField(
        default=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Operational state shown to students — separate from is_active, "
                   "which controls whether the kitchen appears in the system at all.",
    )

    status_note = models.CharField(
        max_length=255,
        blank=True,
        help_text="e.g. 'Closed for deep cleaning until Friday'",
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return self.name

class VolunteerProfile(models.Model):
 
    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        related_name="volunteer_profiles",
    )
 
    name = models.CharField(max_length=255)
    matrik_no = models.CharField(max_length=50, blank=True, help_text="Matriculation number")
    phone_number = models.CharField(max_length=20, blank=True)
    faculty = models.CharField(max_length=255, blank=True)
    kolej = models.CharField(max_length=255, blank=True, help_text="Residential college")
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["name"]
 
    def __str__(self):
        return f"{self.name} ({self.kitchen.code})"
 
 
class VolunteerShift(models.Model):

    volunteer = models.ForeignKey(
        VolunteerProfile,
        on_delete=models.CASCADE,
        related_name="shifts",
    )
 
    clock_in = models.DateTimeField(default=timezone.now)
    clock_out = models.DateTimeField(null=True, blank=True)
 
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="What the volunteer worked on this shift, e.g. 'Restocked pantry shelves'",
    )
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ["-clock_in"]
 
    @property
    def kitchen(self):
        return self.volunteer.kitchen
 
    @property
    def is_active(self):
        return self.clock_out is None
 
    @property
    def duration_minutes(self):
        end = self.clock_out or timezone.now()
        return int((end - self.clock_in).total_seconds() // 60)
 
    def __str__(self):
        return f"{self.volunteer.name} ({self.clock_in.date()})"