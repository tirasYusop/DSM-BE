from django.contrib import admin

from .models import (
    AttendanceSession,
    AttendanceRecord,
    StudentActivity,
    FoodbankTakenItem,
)


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "date",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
        "date",
    )

    search_fields = (
        "date",
    )

    ordering = (
        "-date",
    )


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "kitchen",
        "attendance_type",
        "booking",
        "session",
        "check_in_time",
    )

    list_filter = (
        "attendance_type",
        "kitchen",
        "session",
        "check_in_time",
    )

    search_fields = (
        "student__name",
        "student__student_id",
        "kitchen__code",
    )

    readonly_fields = (
        "check_in_time",
    )

    ordering = (
        "-check_in_time",
    )


@admin.register(StudentActivity)
class StudentActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "student",
        "kitchen",
        "attendance",
        "took_rice",
        "took_dish",
        "took_foodbank",
        "used_kitchen",
        "created_at",
    )

    list_filter = (
        "kitchen",
        "took_rice",
        "took_dish",
        "took_foodbank",
        "used_kitchen",
        "created_at",
    )

    search_fields = (
        "student__name",
        "student__student_id",
        "kitchen__code",
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(FoodbankTakenItem)
class FoodbankTakenItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "activity",
        "student",
        "item",
        "quantity",
    )

    list_filter = (
        "item",
    )

    search_fields = (
        "activity__student__name",
        "activity__student__student_id",
        "item__name",
    )

    autocomplete_fields = (
        "activity",
        "item",
    )

    def student(self, obj):
        return obj.activity.student

    student.admin_order_field = "activity__student"
    student.short_description = "Student"