from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .api.serializers import FeedbackSerializer
from rest_framework.response import Response
from django.db.models import Avg, Count
from rest_framework.decorators import action
from .models import Feedback
from rest_framework.permissions import IsAuthenticated
from config.paginations import DefaultPagination

from .models import (Student,)
from .api.serializers import (StudentSerializer)
from apps.users.permissions import IsManagement


class StudentViewSet(viewsets.ModelViewSet):

    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]


class FeedbackViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackSerializer
    pagination_class = DefaultPagination

    def get_queryset(self):
        queryset = Feedback.objects.select_related("student", "kitchen").all().order_by("-created_at")
        user = self.request.user
        role = getattr(user, "role", None)
        if role == "student":
            try:
                queryset = queryset.filter(student=user.student_profile)
            except Exception:
                return queryset.none()

        kitchen_id = self.request.query_params.get("kitchen")
        if kitchen_id:
            queryset = queryset.filter(kitchen_id=kitchen_id)

        rating = self.request.query_params.get("rating")
        if rating:
            queryset = queryset.filter(rating=rating)

        return queryset

    def create(self, request, *args, **kwargs):
        try:
            student = request.user.student_profile
        except Exception:
            return Response({"error": "Student profile not found"}, status=400)

        rating = request.data.get("rating")
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            return Response({"error": "Rating must be a number"}, status=400)

        if rating < 1 or rating > 5:
            return Response({"error": "Rating must be between 1 and 5"}, status=400)

        feedback = Feedback.objects.create(
            student=student,
            kitchen_id=request.data.get("kitchen") or None,
            rating=rating,
            comment=request.data.get("comment", ""),
        )

        return Response(FeedbackSerializer(feedback).data, status=201)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = Feedback.objects.all()
        kitchen_id = request.query_params.get("kitchen")
        if kitchen_id:
            queryset = queryset.filter(kitchen_id=kitchen_id)

        stats = queryset.aggregate(
            average_rating=Avg("rating"),
            total_feedback=Count("id"),
        )

        rating_breakdown = (
            queryset.values("rating")
            .annotate(total=Count("id"))
            .order_by("rating")
        )

        breakdown = {i: 0 for i in range(1, 6)}
        for r in rating_breakdown:
            breakdown[r["rating"]] = r["total"]

        return Response({
            "average_rating": round(stats["average_rating"] or 0, 2),
            "total_feedback": stats["total_feedback"] or 0,
            "rating_breakdown": breakdown,
        })