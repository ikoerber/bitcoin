"""
Background Data Updater Service

Handles automatic updates of OHLCV data from Binance using APScheduler.
Runs in a background thread without blocking Django request handling.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger(__name__)

# Thread lock to prevent concurrent updates of the same timeframe
update_locks = {
    '15m': Lock(),
    '1h': Lock(),
    '4h': Lock(),
    '1d': Lock()
}


class DataUpdateService:
    """Service for updating OHLCV data in background."""

    def __init__(self):
        """Initialize the data update service."""
        self.last_update_times = {}
        self.update_stats = {}

    def update_timeframe(self, timeframe: str) -> dict:
        """
        Update a specific timeframe in background.

        Args:
            timeframe: Timeframe to update (15m, 1h, 4h, 1d)

        Returns:
            Dictionary with update statistics
        """
        # Acquire lock for this timeframe (prevent concurrent updates)
        if not update_locks[timeframe].acquire(blocking=False):
            logger.warning(f"Skipping {timeframe} update - previous update still in progress")
            return {
                'timeframe': timeframe,
                'status': 'skipped',
                'reason': 'previous_update_in_progress'
            }

        try:
            start_time = datetime.now()
            logger.info(f"Starting background update for {timeframe} timeframe")

            # Import db_manager dynamically to avoid circular imports
            # Use the parent directory's db_manager.py
            from django.conf import settings
            parent_dir = settings.BASE_DIR.parent

            # Add parent directory to Python path if not already there
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))

            # Import BTCDataManager
            from db_manager import BTCDataManager

            # Initialize manager with explicit database path
            db_path = settings.DATABASES['default']['NAME']
            manager = BTCDataManager(db_name=str(db_path))

            # Update only the specified timeframe
            inserted = manager.update_timeframe(timeframe)

            duration = (datetime.now() - start_time).total_seconds()

            # Store statistics
            result = {
                'timeframe': timeframe,
                'status': 'success',
                'inserted': inserted,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }

            self.last_update_times[timeframe] = datetime.now()
            self.update_stats[timeframe] = result

            logger.info(
                f"Background update completed for {timeframe}: "
                f"{inserted} new candles in {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error updating {timeframe} timeframe: {e}", exc_info=True)
            return {
                'timeframe': timeframe,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            # Always release the lock
            update_locks[timeframe].release()

    def get_last_update_time(self, timeframe: str):
        """Get the last successful update time for a timeframe."""
        return self.last_update_times.get(timeframe)

    def get_update_stats(self, timeframe: str = None):
        """Get update statistics for timeframe(s)."""
        if timeframe:
            return self.update_stats.get(timeframe)
        return self.update_stats

    def check_health(self, timeframe: str, max_age_minutes: int = 10) -> dict:
        """
        Check if updates are running healthy for a timeframe.

        Args:
            timeframe: Timeframe to check
            max_age_minutes: Maximum acceptable age of last update

        Returns:
            Dictionary with health status
        """
        last_update = self.last_update_times.get(timeframe)

        if last_update is None:
            return {
                'healthy': False,
                'reason': 'no_updates_yet',
                'timeframe': timeframe
            }

        age = datetime.now() - last_update
        threshold = timedelta(minutes=max_age_minutes)

        if age > threshold:
            return {
                'healthy': False,
                'reason': 'stale_data',
                'last_update': last_update.isoformat(),
                'age_minutes': age.total_seconds() / 60,
                'threshold_minutes': max_age_minutes,
                'timeframe': timeframe
            }

        return {
            'healthy': True,
            'last_update': last_update.isoformat(),
            'age_minutes': age.total_seconds() / 60,
            'timeframe': timeframe
        }


# Global singleton instance
_service_instance = None


def get_data_update_service():
    """Get or create the singleton DataUpdateService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataUpdateService()
    return _service_instance
