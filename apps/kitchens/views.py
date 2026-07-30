from django.conf import settings
from rest_framework import viewsets,serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Kitchen,VolunteerProfile,VolunteerShift
from .api.serializers import KitchenSerializer, VolunteerProfileSerializer,VolunteerShiftSerializer
from django.utils import timezone

class KitchenViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]
    serializer_class = KitchenSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "management":
            return Kitchen.objects.filter(
                is_active=True
            ).order_by(
                "-created_at"
            )

        if user.role == "student":
            return Kitchen.objects.filter(
                is_active=True
            ).order_by(
                "name"
            )

        if user.role == "volunteer":
            if user.kitchen:
                return Kitchen.objects.filter(
                    id=user.kitchen.id,
                    is_active=True
                )

        return Kitchen.objects.none()

    @action(detail=True, methods=["get"], url_path="qr")
    def kitchen_qr(self, request, pk=None):
        kitchen = self.get_object()
        return Response({
            "kitchen_id": kitchen.id,
            "kitchen_name": kitchen.name,
            "kitchen_code": kitchen.code,
            "qr_url": f"{settings.FRONTEND_URL}/student/scan?kitchen={kitchen.id}"
        })



class VolunteerProfileViewSet(viewsets.ModelViewSet):
    """
    The roster of registered volunteers. Volunteers register themselves once
    (name, faculty, kolej); after that they just pick their name from this
    list to clock in/out — no individual login required.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerProfileSerializer
    queryset = VolunteerProfile.objects.all()
 
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)
 
        if role == "management":
            kitchen = self.request.query_params.get("kitchen")
            if kitchen:
                queryset = queryset.filter(kitchen_id=kitchen)
            return queryset
 
        kitchen = getattr(user, "kitchen", None)
        if not kitchen:
            return queryset.none()
        return queryset.filter(kitchen=kitchen)
 
    def perform_create(self, serializer):
        user = self.request.user
        role = getattr(user, "role", None)
 
        if role == "management":
            kitchen_id = self.request.data.get("kitchen")
            if not kitchen_id:
                raise serializers.ValidationError({"kitchen": "This field is required."})
            serializer.save(kitchen_id=kitchen_id)
        else:
            kitchen = getattr(user, "kitchen", None)
            serializer.save(kitchen=kitchen)
 
 
class VolunteerShiftViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = VolunteerShiftSerializer
    queryset = VolunteerShift.objects.all()
 
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)
 
        if role == "management":
            kitchen = self.request.query_params.get("kitchen")
            if kitchen:
                queryset = queryset.filter(volunteer__kitchen_id=kitchen)
            return queryset
 
        kitchen = getattr(user, "kitchen", None)
        if not kitchen:
            return queryset.none()
        return queryset.filter(volunteer__kitchen=kitchen)
 
    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """The open shift (clock_out is null) for a given volunteer profile, if any."""
        volunteer_id = request.query_params.get("volunteer")
        if not volunteer_id:
            return Response({"error": "volunteer is required"}, status=400)
 
        shift = VolunteerShift.objects.filter(
            volunteer_id=volunteer_id, clock_out__isnull=True
        ).first()
 
        if not shift:
            return Response(None)
 
        return Response(VolunteerShiftSerializer(shift).data)
 
    @action(detail=False, methods=["post"], url_path="clock-in")
    def clock_in(self, request):
        volunteer_id = request.data.get("volunteer")
        try:
            volunteer = VolunteerProfile.objects.get(id=volunteer_id)
        except VolunteerProfile.DoesNotExist:
            return Response({"error": "Invalid volunteer"}, status=400)
 
        already_open = VolunteerShift.objects.filter(
            volunteer=volunteer, clock_out__isnull=True
        ).exists()
        if already_open:
            return Response({"error": f"{volunteer.name} is already clocked in"}, status=400)
 
        shift = VolunteerShift.objects.create(
            volunteer=volunteer,
            notes=request.data.get("notes", ""),
        )
        return Response(VolunteerShiftSerializer(shift).data, status=201)
 
    @action(detail=False, methods=["post"], url_path="clock-out")
    def clock_out(self, request):
        volunteer_id = request.data.get("volunteer")
        shift = VolunteerShift.objects.filter(
            volunteer_id=volunteer_id, clock_out__isnull=True
        ).first()
 
        if not shift:
            return Response({"error": "This volunteer isn't currently clocked in"}, status=400)
 
        shift.clock_out = timezone.now()
        notes = request.data.get("notes")
        if notes:
            shift.notes = notes
        shift.save()
 
        return Response(VolunteerShiftSerializer(shift).data)