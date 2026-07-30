from django.core.management.base import BaseCommand
from datetime import date, timedelta, time
from apps.kitchens.models import Kitchen
from apps.booking.models import KitchenSlot

class Command(BaseCommand):

    help = "Generate kitchen slots for the next N days (default 10), per active kitchen"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=10,
            help="How many days ahead (starting today) to generate slots for."
        )

    def handle(self, *args, **kwargs):

        today = date.today()
        days = kwargs["days"]
        kitchens = Kitchen.objects.filter(is_active=True)

        if not kitchens.exists():
            self.stdout.write(
                self.style.WARNING("No active kitchens found — nothing to generate.")
            )
            return

        slots = [
            (time(8, 0), time(8, 30)),
            (time(8, 30), time(9, 0)),
            (time(9, 0), time(9, 30)),
            (time(9, 30), time(10, 0)),
            (time(14, 0), time(14, 30)),
            (time(14, 30), time(15, 0)),
            (time(15, 0), time(15, 30)),
            (time(15, 30), time(16, 0)),
            (time(16, 0), time(16, 30)),
            (time(16, 30), time(17, 0)),
            (time(17, 0), time(17, 30)),
            (time(17, 30), time(18, 0)),
        ]

        for i in range(days):

            current_date = today + timedelta(days=i)

            for kitchen in kitchens:

                for start, end in slots:
                    _, created = KitchenSlot.objects.get_or_create(
                        kitchen=kitchen,
                        date=current_date,
                        start_time=start,
                        end_time=end,
                        defaults={
                            "max_capacity": 2,
                            "current_booking": 0,
                            "status": "available",
                        }
                    )

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created {kitchen.name} {current_date} {start}-{end}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"Already exists {kitchen.name} {current_date} {start}"
                        )