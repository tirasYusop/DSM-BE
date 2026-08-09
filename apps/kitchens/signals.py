from datetime import date, timedelta, time
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Kitchen, ShiftSlot
from apps.booking.models import KitchenSlot

DEFAULT_SLOTS = [
    ("7am-11am Penyediaan Makanan", "food_prep", "07:00", "11:00", 2),
    ("11am-2pm Krew Khidmat Pelanggan", "customer_service", "11:00", "14:00", 1),
    ("4pm-8pm Krew Penyediaan Makanan", "food_prep", "16:00", "20:00", 4),
    ("8pm-11pm Krew Khidmat Pelanggan", "customer_service", "20:00", "23:00", 1),
]

BOOKING_SLOT_TIMES = [
    (time(8, 0), time(8, 30)), (time(8, 30), time(9, 0)),
    (time(9, 0), time(9, 30)), (time(9, 30), time(10, 0)),
    (time(14, 0), time(14, 30)), (time(14, 30), time(15, 0)),
    (time(15, 0), time(15, 30)), (time(15, 30), time(16, 0)),
    (time(16, 0), time(16, 30)), (time(16, 30), time(17, 0)),
    (time(17, 0), time(17, 30)), (time(17, 30), time(18, 0)),
]


@receiver(post_save, sender=Kitchen)
def create_default_shift_slots(sender, instance, created, **kwargs):
    if not created:
        return
    ShiftSlot.objects.bulk_create([
        ShiftSlot(
            kitchen=instance,
            name=name,
            slot_type=slot_type,
            start_time=start,
            end_time=end,
            capacity=capacity,
        )
        for name, slot_type, start, end, capacity in DEFAULT_SLOTS
    ])


@receiver(post_save, sender=Kitchen)
def create_initial_booking_slots(sender, instance, created, **kwargs):
    if not created:
        return
    
    today = date.today()
    slots_to_create = []
    for i in range(10):
        current_date = today + timedelta(days=i)
        for start, end in BOOKING_SLOT_TIMES:
            slots_to_create.append(
                KitchenSlot(
                    kitchen=instance,
                    date=current_date,
                    start_time=start,
                    end_time=end,
                    max_capacity=2,
                    current_booking=0,
                    status="available",
                )
            )
    KitchenSlot.objects.bulk_create(slots_to_create, ignore_conflicts=True)