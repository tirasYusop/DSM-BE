from rest_framework import serializers
from ..models import StudentStorageLog


class StudentStorageLogSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source="student.email", read_only=True)
    kitchen_name = serializers.CharField(source="kitchen.code", read_only=True)
    expiry_date = serializers.DateField(read_only=True)
    days_left = serializers.IntegerField(read_only=True)
    is_past_limit = serializers.BooleanField(read_only=True)

    def get_student_name(self, obj):
        full_name = obj.student.get_full_name()
        if full_name:
            return full_name
        return getattr(obj.student, "username", None) or obj.student.email

    class Meta:
        model = StudentStorageLog
        fields = [
            "id", "student", "student_name", "student_email", "kitchen", "kitchen_name",
            "item_name", "date_stored", "proof_image", "status",
            "expiry_date", "days_left", "is_past_limit",
            "removed_at", "created_at",
        ]
        read_only_fields = ["student", "status", "removed_at", "created_at"]