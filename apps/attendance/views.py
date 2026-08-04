from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from apps.kitchens.models import Kitchen
from apps.booking.models import KitchenBooking
from apps.users.permissions import IsManagement
from .models import (AttendanceRecord,AttendanceSession,StudentActivity, FoodbankTakenItem)
from .api.serializers import AttendanceSerializer,StudentActivitySerializer
from django.db import transaction
from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.views import get_current_stock
from django.db.models import Count
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from apps.students.models import Student 

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
@permission_classes([IsManagement])
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
@permission_classes([IsManagement])
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
@permission_classes([IsManagement])
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
@permission_classes([IsManagement])
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
class StudentSummaryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        records = AttendanceRecord.objects.select_related("student", "kitchen")
        total_records = records.count()
        by_kitchen_qs = (
            records.exclude(kitchen__isnull=True)
            .values("kitchen__id", "kitchen__name")
            .annotate(total=Count("id"))
            .order_by("-total")
        )
        by_kitchen = [
            {
                "kitchen_id": r["kitchen__id"],
                "kitchen_name": r["kitchen__name"],
                "total": r["total"],
            }
            for r in by_kitchen_qs
        ]
        category_counts = {choice[0]: 0 for choice in Student.CATEGORY_CHOICES}
        by_category_qs = (
            records.values("student__category")
            .annotate(total=Count("id"))
        )
        for r in by_category_qs:
            category = r["student__category"] or "OTHERS"
            if category in category_counts:
                category_counts[category] += r["total"]
            else:
                category_counts["OTHERS"] += r["total"]

        by_category = [
            {"category": category, "total": total}
            for category, total in category_counts.items()
        ]
        purpose_counts = {
            "take_rice": 0,
            "take_rice_and_dish": 0,
            "use_kitchen": 0,
            "take_rice_and_use_kitchen": 0,
        }

        activities = StudentActivity.objects.only(
            "took_rice", "took_dish", "used_kitchen"
        )

        for a in activities:
            if a.took_rice and a.used_kitchen:
                purpose_counts["take_rice_and_use_kitchen"] += 1
            elif a.took_rice and a.took_dish:
                purpose_counts["take_rice_and_dish"] += 1
            elif a.used_kitchen:
                purpose_counts["use_kitchen"] += 1
            elif a.took_rice:
                purpose_counts["take_rice"] += 1

        monthly_qs = (
            records.exclude(check_in_time__isnull=True)
            .annotate(month=TruncMonth("check_in_time"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )
        monthly_data = [
            {"month": m["month"].strftime("%Y-%m"), "total": m["total"]}
            for m in monthly_qs
        ]
        total_all_months = sum(m["total"] for m in monthly_data)

        return Response({
            "total_records": total_records,
            "by_kitchen": by_kitchen,
            "by_category": by_category,
            "by_purpose": purpose_counts,
            "monthly_summary": {
                "data": monthly_data,
                "total_all": total_all_months,
            },
        })