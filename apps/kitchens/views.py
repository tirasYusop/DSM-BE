from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsManagement, IsManagementOrVolunteer
from .models import Kitchen, VolunteerProfile, VolunteerShift, ShiftSlot, ScheduledShift
from .api.serializers import KitchenSerializer, VolunteerProfileSerializer, VolunteerShiftSerializer, ScheduledShiftSerializer, ShiftSlotSerializer
from django.utils import timezone

User = get_user_model()

class KitchenViewSet(viewsets.ModelViewSet):

    serializer_class = KitchenSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == "management":
            return Kitchen.objects.filter(is_active=True).order_by("-created_at")

        if user.role == "student":
            return Kitchen.objects.filter(is_active=True).order_by("name")

        if user.role == "volunteer":
            if user.kitchen:
                return Kitchen.objects.filter(id=user.kitchen.id, is_active=True)

        return Kitchen.objects.none()

    def destroy(self, request, *args, **kwargs):
        kitchen = self.get_object()
        kitchen.is_active = False
        kitchen.save()
        return Response({"message": "Kitchen deactivated"}, status=200)

    @action(detail=True, methods=["get"], url_path="qr")
    def kitchen_qr(self, request, pk=None):
        kitchen = self.get_object()
        return Response({
            "kitchen_id": kitchen.id,
            "kitchen_name": kitchen.name,
            "kitchen_code": kitchen.code,
            "qr_url": f"{settings.FRONTEND_URL}/student/scan?kitchen={kitchen.id}"
        })

    @action(detail=True, methods=["post"], url_path="reset-credentials", permission_classes=[IsManagement])
    def reset_credentials(self, request, pk=None):
        kitchen = self.get_object()
        new_password = request.data.get("password")
        if not new_password:
            return Response({"error": "password is required"}, status=400)
        try:
            validate_password(new_password)
        except Exception as e:
            raise ValidationError({"password": list(e.messages)})

        user = User.objects.filter(kitchen=kitchen, role="volunteer").first()
        if not user:
            return Response({"error": "No account exists for this kitchen"}, status=404)

        user.set_password(new_password)
        user.save()
        return Response({"message": "Password updated"})

    @action(detail=True, methods=["post"], url_path="update-credentials", permission_classes=[IsManagement])
    def update_credentials(self, request, pk=None):
        kitchen = self.get_object()
        new_username = request.data.get("username")
        new_password = request.data.get("password")

        if not new_username and not new_password:
            return Response({"error": "Provide username and/or password to update"}, status=400)

        user = User.objects.filter(kitchen=kitchen, role="volunteer").first()
        if not user:
            return Response({"error": "No account exists for this kitchen"}, status=404)

        if new_username and new_username != user.username:
            if User.objects.exclude(id=user.id).filter(username=new_username).exists():
                return Response({"error": "Username already taken"}, status=400)
            user.username = new_username

        if new_password:
            try:
                validate_password(new_password)
            except Exception as e:
                raise ValidationError({"password": list(e.messages)})
            user.set_password(new_password)

        user.save()
        return Response({"message": "Credentials updated", "username": user.username})


class VolunteerProfileViewSet(viewsets.ModelViewSet):
    serializer_class = VolunteerProfileSerializer
    queryset = VolunteerProfile.objects.all()

    def get_permissions(self):
        return [IsManagementOrVolunteer()]

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
    serializer_class = VolunteerShiftSerializer
    queryset = VolunteerShift.objects.all()

    def get_permissions(self):
        return [IsManagementOrVolunteer()]

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

class ShiftSlotViewSet(viewsets.ModelViewSet):
    serializer_class = ShiftSlotSerializer
    queryset = ShiftSlot.objects.all()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagementOrVolunteer()]
        return [IsAuthenticated()]

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
            if not kitchen:
                raise serializers.ValidationError({"kitchen": "No kitchen assigned to this account."})
            serializer.save(kitchen=kitchen)

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


class ScheduledShiftViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduledShiftSerializer
    queryset = ScheduledShift.objects.all()

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        role = getattr(user, "role", None)

        if role == "management":
            kitchen = self.request.query_params.get("kitchen")
            if kitchen:
                queryset = queryset.filter(slot__kitchen_id=kitchen)
        else:
            kitchen = getattr(user, "kitchen", None)
            if not kitchen:
                return queryset.none()
            queryset = queryset.filter(slot__kitchen=kitchen)

        date = self.request.query_params.get("date")
        if date:
            queryset = queryset.filter(date=date)
        return queryset

    @action(detail=False, methods=["get"], url_path="week")
    def week(self, request):
        from datetime import timedelta

        start = request.query_params.get("start")
        start_date = timezone.datetime.strptime(start, "%Y-%m-%d").date() if start else timezone.now().date()

        user = request.user
        if getattr(user, "role", None) == "management":
            kitchen_id = request.query_params.get("kitchen")
        else:
            kitchen = getattr(user, "kitchen", None)
            if not kitchen:
                return Response([])
            kitchen_id = kitchen.id

        slots = ShiftSlot.objects.filter(kitchen_id=kitchen_id) if kitchen_id else ShiftSlot.objects.none()

        days = [start_date + timedelta(days=i) for i in range(7)]
        result = []
        for day in days:
            day_slots = []
            for slot in slots:
                assigned = ScheduledShift.objects.filter(slot=slot, date=day).select_related("volunteer")
                day_slots.append({
                    "slot": ShiftSlotSerializer(slot).data,
                    "assigned": ScheduledShiftSerializer(assigned, many=True).data,
                    "open_spots": slot.capacity - assigned.count(),
                })
            result.append({"date": day.isoformat(), "slots": day_slots})

        return Response(result)