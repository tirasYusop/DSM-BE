from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from apps.inventory.models import StudentStorageLog


class Command(BaseCommand):
    help = (
        "Finds storage logs past the 3-day limit that are still marked 'stored', "
        "flips them to 'expired', and emails the student + management. "
        "Intended to run once a day via cron or Celery beat — "
        "e.g. a daily cron entry: 0 8 * * * python manage.py check_storage_expiry"
    )

    def handle(self, *args, **options):
        candidates = StudentStorageLog.objects.filter(status="stored")
        expired = [log for log in candidates if log.is_past_limit]

        if not expired:
            self.stdout.write("No newly expired storage logs.")
            return

        # People with the "management" role who have an email on file
        User = expired[0].student.__class__
        management_emails = list(
            User.objects.filter(role="management")
            .exclude(email="")
            .values_list("email", flat=True)
        )

        for log in expired:
            log.status = "expired"
            log.notified_at = timezone.now()
            log.save()

            subject = f"Storage limit passed: {log.item_name} ({log.kitchen.code})"
            message = (
                f"{log.item_name} was placed in {log.kitchen.code}'s storage on "
                f"{log.date_stored} and has passed the {log.expiry_date} limit. "
                f"Please remove or discard it."
            )

            recipients = list(management_emails)
            if log.student.email:
                recipients.append(log.student.email)

            if recipients:
                send_mail(
                    subject,
                    message,
                    getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipients,
                    fail_silently=True,
                )

        self.stdout.write(f"Flagged and notified for {len(expired)} expired storage log(s).")