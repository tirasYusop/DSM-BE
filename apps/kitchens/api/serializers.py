from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from ..models import Kitchen, VolunteerShift, VolunteerProfile, ShiftSlot, ScheduledShift

User = get_user_model()


class KitchenSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Kitchen
        fields = "__all__"

    def validate(self, data):
        if self.instance is None:
            username = data.get("username")
            password = data.get("password")
            if not username or not password:
                raise serializers.ValidationError(
                    "username and password are required to register a kitchen."
                )
            if User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": "Username already taken."})
            validate_password(password)
        return data

    def create(self, validated_data):
        username = validated_data.pop("username")
        password = validated_data.pop("password")

        with transaction.atomic():
            kitchen = Kitchen.objects.create(**validated_data)
            User.objects.create_user(
                username=username,
                password=password,
                role="volunteer",
                kitchen=kitchen,
            )
        return kitchen
class VolunteerProfileSerializer(serializers.ModelSerializer):
    kitchen_name = serializers.CharField(source="kitchen.code", read_only=True)

    class Meta:
        model = VolunteerProfile
        fields = ["id", "kitchen", "kitchen_name", "name", "matrik_no", "phone_number", "faculty", "kolej", "created_at"]
        read_only_fields = ["kitchen", "created_at"]


class VolunteerShiftSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.name", read_only=True)
    kitchen_name = serializers.CharField(source="volunteer.kitchen.code", read_only=True)
    duration_minutes = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = VolunteerShift
        fields = [
            "id", "volunteer", "volunteer_name", "kitchen_name",
            "clock_in", "clock_out", "notes", "duration_minutes", "is_active",
            "created_at",
        ]
        read_only_fields = ["clock_in", "clock_out", "created_at"]


class ShiftSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftSlot
        fields = ["id", "kitchen", "name", "slot_type", "start_time", "end_time", "capacity"]


class ScheduledShiftSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source="volunteer.name", read_only=True)
    slot_name = serializers.CharField(source="slot.name", read_only=True)

    class Meta:
        model = ScheduledShift
        fields = ["id", "slot", "slot_name", "volunteer", "volunteer_name", "date", "created_at"]

    def validate(self, data):
        slot = data.get("slot") or getattr(self.instance, "slot", None)
        date = data.get("date") or getattr(self.instance, "date", None)

        qs = ScheduledShift.objects.filter(slot=slot, date=date)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.count() >= slot.capacity:
            raise serializers.ValidationError(
                f"This slot is already full ({slot.capacity} volunteers) for {date}."
            )
        return data