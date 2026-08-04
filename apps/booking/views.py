from django.utils import timezone
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.users.permissions import IsManagement
from .models import (KitchenSlot,KitchenBooking,BookingParticipant)
from .api.serializers import (KitchenSlotSerializer,KitchenBookingSerializer,)

class KitchenSlotViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = KitchenSlot.objects.all().order_by("date","start_time")
    serializer_class = KitchenSlotSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagement()]
        return [IsAuthenticated()]

    @action(detail=False,methods=["get"], url_path="available")
    def available(self, request):
        kitchen_id = request.query_params.get("kitchen")
        now = timezone.localtime()
        today = now.date()
        current_time = now.time()
        slots = KitchenSlot.objects.filter(status="available", date__gte=today)
        slots = slots.exclude(date=today,start_time__lte=current_time)

        if kitchen_id:
            slots = slots.filter(kitchen_id=kitchen_id)

        slots = slots.order_by("date", "start_time" )
        serializer = KitchenSlotSerializer(slots, many=True)
        return Response(serializer.data)

class KitchenBookingViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = KitchenBooking.objects.all().order_by("-created_at")
    serializer_class = KitchenBookingSerializer

    @action(detail=False,methods=["get"])
    def my_bookings(self, request):
        try:
            student = request.user.student_profile
        except:
            return Response(
                {"error": "Student profile not found."},status=400
            )
        bookings = KitchenBooking.objects.filter(
            student=student
        ).order_by(
            "-created_at"
        )

        kitchen_id = request.query_params.get("kitchen")
        if kitchen_id:
            bookings = bookings.filter(slot__kitchen_id=kitchen_id)

        serializer = KitchenBookingSerializer(bookings,many=True)
        return Response( serializer.data)

    def create(self, request):
        if request.user.role != "student":
            return Response(
                {
                    "error": "Only students can make booking."
                },
                status=status.HTTP_403_FORBIDDEN
            )
        try:
            student = request.user.student_profile
        except:
            return Response(
                {
                    "error": "Student profile not found."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        slot_id = request.data.get("slot")

        participants = request.data.get("participants",[])
        people = len(participants) + 1

        if people <= 0:
            return Response(
                {
                    "error": "Invalid number of people."
                },
                status=400
            )

        try:
            slot = KitchenSlot.objects.get(
                id=slot_id
            )
        except KitchenSlot.DoesNotExist:
            return Response(
                {
                    "error": "Slot not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.localtime()
        slot_already_passed = (
            slot.date < now.date()
            or (slot.date == now.date() and slot.start_time <= now.time())
        )

        if slot_already_passed:
            return Response(
                {
                    "error": "Cannot book a slot whose time has already passed."
                },
                status=400
            )

        if slot.current_booking >= slot.max_capacity:
            return Response(
                {
                    "error": "Slot is full."
                },
                status=400
            )

        exists = KitchenBooking.objects.filter(
            student=student,
            slot=slot,
            status__in=[
                "pending",
                "approved"
            ]
        ).exists()

        if exists:
            return Response(
                {
                    "error": "You already booked this slot."
                },
                status=400
            )

        ids = []

        for p in participants:

            if not p.get("name"):
                return Response(
                    {
                        "error": "Participant name is required."
                    },
                    status=400
                )

            if not p.get("student_id"):
                return Response(
                    {
                        "error": "Participant student ID is required."
                    },
                    status=400
                )

            if not p.get("faculty"):
                return Response(
                    {
                        "error": "Participant faculty is required."
                    },
                    status=400
                )

            if p["student_id"] in ids:
                return Response(
                    {
                        "error": f'Duplicate student ID {p["student_id"]}.'
                    },
                    status=400
                )

            ids.append(
                p["student_id"]
            )

        booking = KitchenBooking.objects.create(
            student=student,
            slot=slot,
            number_of_people=people,
            purpose=request.data.get("purpose","")
        )

        BookingParticipant.objects.create(
            booking=booking,
            name=student.name,
            student_id=student.student_id,
            faculty=getattr(student, "faculty", "") or "",
            is_owner=True
        )

        for p in participants:
            BookingParticipant.objects.create(
                booking=booking,
                name=p["name"],
                student_id=p["student_id"],
                faculty=p["faculty"]
            )

        slot.current_booking += 1
        if slot.current_booking >= slot.max_capacity:
            slot.status = "full"

        slot.save()

        serializer = KitchenBookingSerializer(booking)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True,methods=["post"])
    def cancel(self,request,pk=None):
        try:
            student = request.user.student_profile
        except:
            return Response(
                {
                    "error": "Student profile not found."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        booking = self.get_object()
        if booking.student != student:
            return Response(
                {"error": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )
        if booking.status == "cancelled":
            return Response(
                {
                    "error": "Booking already cancelled."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if booking.attended:
            return Response(
                {
                    "error": "Cannot cancel a booking that has already been checked in."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.localtime()
        slot = booking.slot
        already_passed = (
            slot.date < now.date()
            or (slot.date == now.date() and slot.end_time <= now.time())
        )
        if already_passed:
            return Response(
                {"error": "Cannot cancel a booking whose slot time has already passed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = "cancelled"
        booking.save()
        slot = booking.slot
        slot.current_booking = max(0, slot.current_booking - 1)
        if slot.current_booking < slot.max_capacity:
            slot.status = "available"
        slot.save()
        return Response(
            {
                "message": "Booking cancelled."
            }
        )
 
    @action(detail=False, methods=["get"], url_path="roster")
    def roster(self, request):
        if request.user.role not in ["volunteer", "management"]:
            return Response(
                {"error": "Not allowed."},
                status=status.HTTP_403_FORBIDDEN,
            )
        kitchen = getattr(request.user, "kitchen", None)
    
        if request.user.role == "volunteer" and kitchen is None:
            return Response(
                {"error": "No kitchen linked to this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    
        date_param = request.query_params.get("date")
        target_date = date_param or timezone.localtime().date().isoformat()
    
        bookings = (
            KitchenBooking.objects.filter(
                slot__date=target_date,
            )
            .exclude(status="cancelled")
            .select_related("slot", "slot__kitchen", "student")
            .prefetch_related("participants")
            .order_by("slot__start_time", "-created_at")
        )
    
        if request.user.role == "volunteer":
            bookings = bookings.filter(slot__kitchen=kitchen)
        else:
            kitchen_id = request.query_params.get("kitchen")
            if kitchen_id:
                bookings = bookings.filter(slot__kitchen_id=kitchen_id)
    
        serializer = KitchenBookingSerializer(bookings, many=True)
        return Response(serializer.data)