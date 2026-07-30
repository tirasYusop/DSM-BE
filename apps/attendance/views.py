from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from apps.kitchens.models import Kitchen
from apps.booking.models import KitchenBooking
from .models import (AttendanceRecord,AttendanceSession,StudentActivity, FoodbankTakenItem)
from .api.serializers import AttendanceSerializer,StudentActivitySerializer
from django.db import transaction
from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.views import get_current_stock

@api_view(["POST"])
def mark_attendance(request):

    try:
        student = request.user.student_profile

    except Exception:
        return Response(
            {
                "error": "Student profile not found"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    session, created = AttendanceSession.objects.get_or_create(
        date=timezone.now().date(),
        defaults={
            "is_active": True
        }
    )

    booking_id = request.data.get("booking")
    kitchen_id = request.data.get("kitchen")
    attendance_type = "walk_in"
    booking = None
    kitchen = None

    if kitchen_id:
        try:
            kitchen = Kitchen.objects.get(id=kitchen_id)

        except Kitchen.DoesNotExist:

            return Response(
                {
                    "error":"Kitchen not found"
                },
                status=404
            )


    if booking_id:
        try:
            booking = KitchenBooking.objects.get(id=booking_id)

        except KitchenBooking.DoesNotExist:
            return Response(
                {
                    "error": "Booking not found"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if booking.student != student:
            return Response(
                {
                    "error": "Invalid booking"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        attendance_type = "booking"
        booking_kitchen = booking.slot.kitchen

        if (
            kitchen is not None
            and booking_kitchen is not None
            and kitchen.id != booking_kitchen.id
        ):
            return Response(
                {
                    "error": "This booking is for a different kitchen."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        kitchen = booking_kitchen

    attendance = AttendanceRecord.objects.create(
        session=session,
        student=student,
        booking=booking,
        kitchen=kitchen,
        attendance_type=attendance_type
    )

    if booking:
        booking.attended = True
        booking.save()

    return Response(
        {
            "message": "Attendance marked successfully",
            "data": AttendanceSerializer(attendance).data
        },
        status=status.HTTP_201_CREATED
    )

@api_view(["GET"])
def attendance_list(request):

    records = AttendanceRecord.objects.select_related(
        "student",
        "session",
        "booking",
        "kitchen"
    ).all().order_by(
        "-check_in_time"
    )

    serializer = AttendanceSerializer(records, many=True)

    return Response(serializer.data)

@api_view(["GET"])
def management_walkin(request):

    records = AttendanceRecord.objects.filter(
        attendance_type="walk_in"
    ).select_related(
        "student",
        "session",
        "kitchen"
    ).order_by(
        "-check_in_time"
    )


    serializer = AttendanceSerializer(
        records,
        many=True
    )

    return Response(
        serializer.data
    )


@api_view(["GET"])
def management_booking(request):
    
    records = AttendanceRecord.objects.filter(
        attendance_type="booking",
        kitchen__isnull=False
    ).select_related(
        "student",
        "booking",
        "kitchen"
    ).order_by(
        "-check_in_time"
    )

    serializer = AttendanceSerializer(records, many=True)
    return Response(serializer.data)


@api_view(["POST"])
def submit_activity(request):
    try:
        student = request.user.student_profile
    except Exception:
        return Response({"error": "Student profile not found"}, status=400)

    try:
        attendance = AttendanceRecord.objects.get(
            id=request.data.get("attendance"), student=student
        )
    except AttendanceRecord.DoesNotExist:
        return Response({"error": "Invalid attendance record"}, status=400)

    if hasattr(attendance, "activity"):
        return Response({"error": "Activity already recorded for this check-in"}, status=400)

    took_rice = bool(request.data.get("took_rice"))
    took_dish = bool(request.data.get("took_dish"))
    used_kitchen = bool(request.data.get("used_kitchen"))
    took_foodbank = bool(request.data.get("took_foodbank"))
    foodbank_items = request.data.get("foodbank_items", [])

    if took_foodbank and not foodbank_items:
        return Response({"error": "Select at least one foodbank item"}, status=400)

    with transaction.atomic():
        activity = StudentActivity.objects.create(
            attendance=attendance,
            student=student,
            kitchen=attendance.kitchen,
            took_rice=took_rice,
            took_dish=took_dish,
            took_foodbank=took_foodbank,
            used_kitchen=used_kitchen,
        )

        for entry in foodbank_items:
            try:
                quantity = int(entry.get("quantity", 0))
            except (TypeError, ValueError):
                return Response({"error": "Invalid quantity"}, status=400)

            if quantity <= 0:
                return Response({"error": "Quantity must be greater than zero"}, status=400)

            try:
                item = InventoryItem.objects.get(id=entry.get("item"))
            except InventoryItem.DoesNotExist:
                return Response({"error": "Invalid foodbank item"}, status=400)

            available = get_current_stock(item, activity.kitchen, is_foodbank=True)
            if quantity > available:
                return Response(
                    {"error": f"Not enough foodbank stock for {item.name}"}, status=400
                )

            StockMovement.objects.create(
                item=item,
                movement_type="out",
                kitchen=activity.kitchen,
                is_foodbank=True,
                quantity=quantity,
                reason="Taken by student (foodbank)",
                purpose=f"Foodbank pickup - {student}",
            )

            FoodbankTakenItem.objects.create(activity=activity, item=item, quantity=quantity)

    return Response(
        {"message": "Activity recorded", "data": StudentActivitySerializer(activity).data},
        status=201,
    )


@api_view(["GET"])
def foodbank_stock_list(request):
    data = []
    for item in InventoryItem.objects.all():
        available = get_current_stock(item, None)
        if available > 0:
            data.append({"id": item.id, "name": item.name, "unit": item.unit, "available": available})
    return Response(data)


@api_view(["GET"])
def activity_list(request):
    activities = StudentActivity.objects.select_related(
        "student", "kitchen", "attendance"
    ).prefetch_related("foodbank_items__item").order_by("-created_at")

    kitchen_id = request.query_params.get("kitchen")
    if kitchen_id:
        activities = activities.filter(kitchen_id=kitchen_id)

    return Response(StudentActivitySerializer(activities, many=True).data)


@api_view(["GET"])
def my_activity(request):
    try:
        student = request.user.student_profile
    except Exception:
        return Response({"error": "Student profile not found"}, status=400)

    activities = StudentActivity.objects.filter(
        student=student
    ).select_related(
        "kitchen", "attendance"
    ).prefetch_related(
        "foodbank_items__item"
    ).order_by("-created_at")

    limit = request.query_params.get("limit")
    if limit:
        try:
            activities = activities[: int(limit)]
        except ValueError:
            pass

    return Response(StudentActivitySerializer(activities, many=True).data)