import sys
import os
from django.apps import AppConfig


class BookingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'apps.booking'

    def ready(self):
        if "runserver" not in sys.argv or os.environ.get("RUN_MAIN") == "true":
            from .scheduler import start_scheduler
            start_scheduler()
