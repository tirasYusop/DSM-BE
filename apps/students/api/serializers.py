from rest_framework import serializers
from ..models import Student,Feedback


class StudentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = "__all__"





class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    kitchen_name = serializers.CharField(source="kitchen.name", read_only=True, default=None)

    class Meta:
        model = Feedback
        fields = [
            "id",
            "student",
            "student_name",
            "kitchen",
            "kitchen_name",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "student", "created_at"]