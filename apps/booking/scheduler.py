import logging
from apscheduler.schedulers.background import BackgroundScheduler
from django.core.management import call_command

logger = logging.getLogger(__name__)


def generate_slots_job():
    try:
        call_command("generate_slots", days=10)
        logger.info("Daily kitchen slot generation completed.")
    except Exception:
        logger.exception("Daily kitchen slot generation failed.")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        generate_slots_job,
        "cron",
        hour=2,
        minute=0,
        id="generate_slots_daily",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Kitchen slot scheduler started — running daily at 02:00.")