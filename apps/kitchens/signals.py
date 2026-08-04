from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Kitchen, ShiftSlot

DEFAULT_SLOTS = [
    ("7am-11am Penyediaan Makanan", "food_prep", "07:00", "11:00", 2),
    ("11am-2pm Krew Khidmat Pelanggan", "customer_service", "11:00", "14:00", 1),
    ("4pm-8pm Krew Penyediaan Makanan", "food_prep", "16:00", "20:00", 4),
    ("8pm-11pm Krew Khidmat Pelanggan", "customer_service", "20:00", "23:00", 1),
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