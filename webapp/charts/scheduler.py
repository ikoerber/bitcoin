"""
APScheduler Configuration for Automatic Data Updates

Starts a background scheduler that periodically updates OHLCV data.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from .data_updater import get_data_update_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def start_scheduler():
    """
    Start the APScheduler background scheduler.

    This function should be called once during Django startup.
    It creates scheduled jobs for each enabled timeframe.
    """
    global scheduler

    # Don't start if auto-updates are disabled
    if not settings.AUTO_UPDATE_ENABLED:
        logger.info("Auto-update scheduler is DISABLED (set AUTO_UPDATE_ENABLED=True to enable)")
        return

    # Don't start if already running
    if scheduler is not None and scheduler.running:
        logger.warning("Scheduler is already running")
        return

    logger.info("Starting auto-update scheduler...")

    # Create background scheduler (runs in separate thread)
    scheduler = BackgroundScheduler({
        'apscheduler.timezone': settings.TIME_ZONE,
        'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': 1  # Only 1 worker to prevent concurrent DB writes
        },
        'apscheduler.job_defaults.coalesce': True,  # Combine missed runs
        'apscheduler.job_defaults.max_instances': 1  # Only 1 instance per job
    })

    # Get the data update service
    service = get_data_update_service()

    # Add jobs for each enabled timeframe
    interval_map = {
        '15m': settings.AUTO_UPDATE_15M_INTERVAL,
        '1h': settings.AUTO_UPDATE_1H_INTERVAL,
        '4h': settings.AUTO_UPDATE_4H_INTERVAL,
        '1d': settings.AUTO_UPDATE_1D_INTERVAL
    }

    enabled_timeframes = [tf.strip() for tf in settings.AUTO_UPDATE_TIMEFRAMES]

    for timeframe in enabled_timeframes:
        if timeframe not in interval_map:
            logger.warning(f"Unknown timeframe '{timeframe}' in AUTO_UPDATE_TIMEFRAMES")
            continue

        interval_minutes = interval_map[timeframe]

        # Add scheduled job
        scheduler.add_job(
            func=service.update_timeframe,
            trigger=IntervalTrigger(minutes=interval_minutes),
            args=[timeframe],
            id=f'update_{timeframe}',
            name=f'Update {timeframe} data',
            replace_existing=True,
            misfire_grace_time=60  # Allow 60s grace period for missed executions
        )

        logger.info(
            f"Scheduled {timeframe} updates every {interval_minutes} minutes "
            f"(job ID: update_{timeframe})"
        )

    # Add Order Blocks calculation job (runs hourly after 1h OHLCV update)
    scheduler.add_job(
        func=service.update_order_blocks,
        trigger=IntervalTrigger(minutes=60),
        args=['1h'],
        id='update_orderblocks_1h',
        name='Update Order Blocks (1h)',
        replace_existing=True,
        misfire_grace_time=300  # Allow 5min grace period for missed executions
    )

    logger.info("Scheduled Order Blocks updates every 60 minutes (job ID: update_orderblocks_1h)")

    # Start the scheduler
    scheduler.start()
    logger.info(f"Auto-update scheduler started with {len(enabled_timeframes) + 1} jobs (OHLCV + Order Blocks)")


def stop_scheduler():
    """Stop the scheduler (called during Django shutdown)."""
    global scheduler

    if scheduler is not None and scheduler.running:
        logger.info("Stopping auto-update scheduler...")
        scheduler.shutdown(wait=True)
        logger.info("Auto-update scheduler stopped")


def get_scheduler_status():
    """Get the current status of the scheduler and its jobs."""
    global scheduler

    if scheduler is None or not scheduler.running:
        return {
            'running': False,
            'jobs': []
        }

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger)
        })

    return {
        'running': True,
        'jobs': jobs
    }
