from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

_scheduler = BackgroundScheduler()


def start_scheduler() -> None:
    if settings.dev_mode:
        return
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
