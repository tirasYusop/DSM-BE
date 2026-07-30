from rest_framework import serializers

from ..models import AttendanceRecord,FoodbankTakenItem,StudentActivity

from apps.students.models import Student
from apps.booking.models import KitchenBooking
from apps.kitchens.models import Kitchen



class StudentAttendanceSerializer(serializers.ModelSerializer):

    class Meta:

        model = Student

        fields = [
            "id",
            "student_id",
            "name",
            "faculty",
            "course",
            "year",
        ]



class BookingAttendanceSerializer(serializers.ModelSerializer):

    slot = serializers.SerializerMethodField()


    class Meta:

        model = KitchenBooking

        fields = [
            "id",
            "slot",
            "number_of_people",
            "purpose",
            "status",
        ]


    def get_slot(self, obj):

        return {

            "id": obj.slot.id,

            "date": obj.slot.date,

            "start_time": obj.slot.start_time,

            "end_time": obj.slot.end_time,

        }

class KitchenAttendanceSerializer(serializers.ModelSerializer):

    class Meta:

        model = Kitchen

        fields = [
            "id",
            "name",
            "code"
        ]


class AttendanceSerializer(serializers.ModelSerializer):

    student = StudentAttendanceSerializer(
        read_only=True
    )


    booking = BookingAttendanceSerializer(
        read_only=True
    )

    kitchen = KitchenAttendanceSerializer(
        read_only=True
    )


    class Meta:

        model = AttendanceRecord

        fields = [

            "id",

            "student",

            "booking",
            "kitchen",
            "attendance_type",

            "check_in_time"

        ]

class FoodbankTakenItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = FoodbankTakenItem
        fields = ["id", "item", "item_name", "quantity"]


class StudentActivitySerializer(serializers.ModelSerializer):
    foodbank_items = FoodbankTakenItemSerializer(many=True, read_only=True)
    student_name = serializers.CharField(source="student.user.get_full_name", read_only=True)
    kitchen_name = serializers.CharField(source="kitchen.name", read_only=True)

    class Meta:
        model = StudentActivity
        fields = [
            "id", "attendance", "student", "student_name",
            "kitchen", "kitchen_name",
            "took_rice", "took_dish", "took_foodbank", "used_kitchen",
            "foodbank_items", "created_at",
        ]