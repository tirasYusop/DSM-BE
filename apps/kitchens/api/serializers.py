from rest_framework import serializers
from ..models import Kitchen,VolunteerShift,VolunteerProfile


class KitchenSerializer(serializers.ModelSerializer):

    class Meta:

        model = Kitchen

        fields = "__all__"




class VolunteerProfileSerializer(serializers.ModelSerializer):
    kitchen_name = serializers.CharField(source="kitchen.code", read_only=True)
 
    class Meta:
        model = VolunteerProfile
        fields = ["id", "kitchen", "kitchen_name", "name","matrik_no", "phone_number", "faculty", "kolej", "created_at"]
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