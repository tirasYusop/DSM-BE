from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone

from .models import StudentStorageLog
from .api.serializers import StudentStorageLogSerializer


class StudentStorageLogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentStorageLogSerializer
    queryset = StudentStorageLog.objects.all()
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)

        if role == "management":
            kitchen = self.request.query_params.get("kitchen")
            if kitchen:
                queryset = queryset.filter(kitchen_id=kitchen)
            return queryset
        return queryset.filter(student=user)

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=["post"], url_path="remove")
    def remove(self, request, pk=None):
        log = self.get_object()

        if log.status != "stored":
            return Response({"error": "This item is already resolved"}, status=400)

        log.status = "removed"
        log.removed_at = timezone.now()
        log.save()

        return Response({"message": "Marked as removed"})

    @action(detail=False, methods=["get"], url_path="alerts")
    def alerts(self, request):
        queryset = self.get_queryset().filter(status="stored")
        flagged = [log for log in queryset if log.days_left <= 1]

        return Response(
            StudentStorageLogSerializer(flagged, many=True).data
        )