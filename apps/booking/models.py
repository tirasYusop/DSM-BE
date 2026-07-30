from django.db import models
from apps.students.models import Student

class KitchenSlot(models.Model):


    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        related_name="slots",
        null=True,
        blank=True
    )


    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    max_capacity = models.IntegerField(
        default=2
    )
    current_booking = models.IntegerField(
        default=0
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("available","Available"),
            ("full","Full"),
            ("closed","Closed")
        ],
        default="available"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def __str__(self):

        return f"{self.date} {self.start_time}"

class KitchenBooking(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    slot = models.ForeignKey(
        KitchenSlot,
        on_delete=models.CASCADE,
        related_name="bookings"
    )
    number_of_people = models.PositiveIntegerField(
        default=1
    )
    purpose = models.TextField(
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending","Pending"),
            ("approved","Approved"),
            ("cancelled","Cancelled")
        ],
        default="pending"
    )
    attended = models.BooleanField(
        default=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def __str__(self):

        return f"{self.student.name} - {self.slot}"
    
class BookingParticipant(models.Model):
    booking = models.ForeignKey(
        KitchenBooking,
        on_delete=models.CASCADE,
        related_name="participants"
    )

    name = models.CharField(max_length=100)

    student_id = models.CharField(max_length=30)
    faculty = models.CharField(max_length=100, blank=True)
    is_owner = models.BooleanField(default=False)

    def __str__(self):
        return self.name