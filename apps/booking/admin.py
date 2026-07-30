from django.contrib import admin

from .models import (
    KitchenSlot,
    KitchenBooking,
    BookingParticipant,
)


class BookingParticipantInline(admin.TabularInline):
    model = BookingParticipant
    extra = 1
    fields = (
        "name",
        "student_id",
        "faculty",
        "is_owner",
    )


@admin.register(KitchenSlot)
class KitchenSlotAdmin(admin.ModelAdmin):

    list_display = (
        "kitchen",
        "date",
        "start_time",
        "end_time",
        "max_capacity",
        "current_booking",
        "status",
    )

    list_filter = (
        "kitchen",
        "status",
        "date",
    )

    search_fields = (
        "kitchen__name",
        "kitchen__code",
    )

    ordering = (
        "-date",
        "start_time",
    )


@admin.register(KitchenBooking)
class KitchenBookingAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "slot",
        "get_kitchen",
        "number_of_people",
        "status",
        "attended",
        "created_at",
    )

    list_filter = (
        "status",
        "attended",
        "slot__kitchen",
        "created_at",
    )

    search_fields = (
        "student__name",
        "student__student_id",
        "participants__name",
        "participants__student_id",
    )

    inlines = [
        BookingParticipantInline,
    ]

    ordering = (
        "-created_at",
    )


    def get_kitchen(self, obj):
        return obj.slot.kitchen

    get_kitchen.short_description = "Kitchen"


@admin.register(BookingParticipant)
class BookingParticipantAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "student_id",
        "faculty",
        "booking",
        "is_owner",
    )

    list_filter = (
        "faculty",
        "is_owner",
    )

    search_fields = (
        "name",
        "student_id",
        "faculty",
    )