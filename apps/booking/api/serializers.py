from rest_framework import serializers

from apps.students.models import Student
from django.utils import timezone

from ..models import (
    KitchenSlot,
    KitchenBooking,
    BookingParticipant
)

class StudentSerializer(serializers.ModelSerializer):

    class Meta:

        model = Student

        fields = [
            "id",
            "student_id",
            "name",
            "email",
            "faculty",
            "course"
        ]



class KitchenSlotSerializer(serializers.ModelSerializer):

    available_capacity = serializers.SerializerMethodField()
    kitchen_name = serializers.CharField(
        source="kitchen.name",
        read_only=True
    )


    class Meta:

        model = KitchenSlot

        fields = [
            "id",
            "kitchen",
            "kitchen_name",
            "date",
            "start_time",
            "end_time",
            "max_capacity",
            "current_booking",
            "available_capacity",
            "status"
            ]



    def get_available_capacity(self,obj):

        return (
            obj.max_capacity -
            obj.current_booking
        )



class BookingParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingParticipant
        fields = "__all__"

class KitchenBookingSerializer(serializers.ModelSerializer):

    is_passed = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()

    student_name = serializers.CharField(
        source="student.name",
        read_only=True
    )

    slot_detail = KitchenSlotSerializer(
        source="slot",
        read_only=True
    )

    slot_date = serializers.CharField(
        source="slot.date",
        read_only=True
    )

    start_time = serializers.CharField(
        source="slot.start_time",
        read_only=True
    )

    end_time = serializers.CharField(
        source="slot.end_time",
        read_only=True
    )

    participants = BookingParticipantSerializer(
        many=True,
        read_only=True
    )

    kitchen_name = serializers.CharField(
        source="slot.kitchen.name",
        read_only=True
    )


    class Meta:

        model = KitchenBooking

        fields = [
            "id",
            "student",
            "student_name",

            "slot",
            "slot_detail",

            "slot_date",
            "start_time",
            "end_time",
            "kitchen_name",
            "number_of_people",
            "purpose",

            "status",
            "attended",
            "created_at",
            "participants",
            "is_passed",
            "display_status",
        ]

        read_only_fields = [
            "status",
            "attended",
            "created_at"
        ]

    def get_is_passed(self, obj):
        now = timezone.localtime()
        slot = obj.slot
        return (
            slot.date < now.date()
            or (slot.date == now.date() and slot.end_time <= now.time())
        )

    def get_display_status(self, obj):
        if obj.status == "cancelled":
            return "cancelled"
        if obj.attended:
            return "attended"
        if self.get_is_passed(obj):
            return "expired"
        return "confirmed"

