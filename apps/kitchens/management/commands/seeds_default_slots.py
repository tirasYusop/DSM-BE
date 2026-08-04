from django.core.management.base import BaseCommand
from apps.kitchens.models import Kitchen, ShiftSlot
from apps.kitchens.signals import DEFAULT_SLOTS


class Command(BaseCommand):
    help = "Seed the 4 default shift slots for kitchens that don't have any yet"

    def handle(self, *args, **options):
        for kitchen in Kitchen.objects.all():
            if kitchen.shift_slots.exists():
                continue
            ShiftSlot.objects.bulk_create([
                ShiftSlot(kitchen=kitchen, name=n, slot_type=t, start_time=s, end_time=e, capacity=c)
                for n, t, s, e, c in DEFAULT_SLOTS
            ])
            self.stdout.write(f"Seeded slots for {kitchen.name}")