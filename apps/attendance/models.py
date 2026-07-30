from django.db import models
from apps.students.models import Student
from apps.booking.models import KitchenBooking
 
class AttendanceSession(models.Model):
    date = models.DateField(
        unique=True
    )
    is_active = models.BooleanField(
        default=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    
    def __str__(self):
 
        return f"Attendance {self.date}"
 
class AttendanceRecord(models.Model):
    ATTENDANCE_TYPE = [
        (
            "booking",
            "Booking"
        ),
        (
            "walk_in",
            "Walk In"
        )
    ]
 
    session = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="records"
    )
 
    kitchen = models.ForeignKey(
        "kitchens.Kitchen",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attendance_records"
    )
 
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
 
    booking = models.ForeignKey(
        KitchenBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records"
    )
 
    attendance_type = models.CharField(
        max_length=20,
        choices=ATTENDANCE_TYPE
    )
 
    check_in_time = models.DateTimeField(
        auto_now_add=True
    )
 
 
    def __str__(self):
        return (
            f"{self.student.name} "
            f"- "
            f"{self.attendance_type}"
        )
    
class StudentActivity(models.Model):
    attendance = models.OneToOneField(
        AttendanceRecord, on_delete=models.CASCADE, related_name="activity"
    )
    student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="activities"
    )
    kitchen = models.ForeignKey(
        "kitchens.Kitchen", on_delete=models.SET_NULL, null=True
    )
    took_rice = models.BooleanField(default=False)
    took_dish = models.BooleanField(default=False)
    took_foodbank = models.BooleanField(default=False)
    used_kitchen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class FoodbankTakenItem(models.Model):
    activity = models.ForeignKey(
        StudentActivity, on_delete=models.CASCADE, related_name="foodbank_items"
    )
    item = models.ForeignKey("inventory.InventoryItem", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()