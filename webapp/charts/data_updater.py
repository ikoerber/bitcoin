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

    def update_order_blocks(self, timeframe: str = '1h') -> dict:
        """
        Calculate and update Order Blocks for specified timeframe.

        This method:
        1. Fetches recent OHLCV data from database
        2. Runs Order Block analysis using orderblock_analytics.py
        3. Upserts Order Blocks to database (creates new, updates existing)
        4. Returns statistics about the update

        Args:
            timeframe: Timeframe to analyze (default: '1h')

        Returns:
            Dictionary with update statistics:
            - timeframe: str
            - status: 'success' or 'error'
            - created: number of new Order Blocks
            - updated: number of updated Order Blocks
            - duration: processing time in seconds
            - timestamp: ISO format timestamp
        """
        start_time = datetime.now()
        logger.info(f"Starting Order Block calculation for {timeframe}")

        try:
            from django.conf import settings
            from .models import TIMEFRAME_MODELS, OrderBlock1h
            from .orderblock_analytics import OrderBlockAnalyzer
            import pandas as pd

            # Get database path
            db_path = settings.DATABASES['default']['NAME']

            # Fetch OHLCV data (need 500 candles for reliable analysis)
            model = TIMEFRAME_MODELS.get(timeframe)
            if not model:
                return {
                    'timeframe': timeframe,
                    'status': 'error',
                    'error': f'Invalid timeframe: {timeframe}',
                    'timestamp': datetime.now().isoformat()
                }

            # Query latest 500 candles
            queryset = model.objects.order_by('-timestamp')[:500]

            if not queryset.exists():
                logger.warning(f"No OHLCV data available for {timeframe}")
                return {
                    'timeframe': timeframe,
                    'status': 'error',
                    'error': 'No OHLCV data available',
                    'timestamp': datetime.now().isoformat()
                }

            # Convert to DataFrame (reverse to chronological order)
            data = list(queryset.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
            data.reverse()
            df = pd.DataFrame(data)

            logger.info(f"Loaded {len(df)} candles for Order Block analysis")

            # Initialize analyzer with configuration
            # TODO: Get these from constants.py or settings
            analyzer = OrderBlockAnalyzer(
                atr_period=14,
                atr_multiplier=1.2,
                swing_window=3,
                zone_mode='conservative',
                min_candles=200
            )

            # Run analysis
            order_blocks = analyzer.analyze(df)

            if not order_blocks:
                logger.info("No Order Blocks detected")
                return {
                    'timeframe': timeframe,
                    'status': 'success',
                    'created': 0,
                    'updated': 0,
                    'duration': (datetime.now() - start_time).total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }

            # Upsert Order Blocks to database
            created_count = 0
            updated_count = 0

            for ob in order_blocks:
                # Check if Order Block already exists
                existing = OrderBlock1h.objects.filter(
                    symbol='BTC/EUR',
                    direction=ob['direction'],
                    created_ts_ms=ob['created_ts_ms']
                ).first()

                if existing:
                    # Update status if changed
                    if existing.status != ob['status']:
                        existing.status = ob['status']
                        existing.valid_to_ts_ms = ob['valid_to_ts_ms']
                        existing.save()
                        updated_count += 1
                else:
                    # Create new Order Block
                    OrderBlock1h.objects.create(
                        symbol='BTC/EUR',
                        direction=ob['direction'],
                        created_ts_ms=ob['created_ts_ms'],
                        valid_from_ts_ms=ob['valid_from_ts_ms'],
                        valid_to_ts_ms=ob['valid_to_ts_ms'],
                        price_low=ob['price_low'],
                        price_high=ob['price_high'],
                        atr14=ob['atr14'],
                        bos_level=ob['bos_level'],
                        displacement_range=ob['displacement_range'],
                        status=ob['status']
                    )
                    created_count += 1

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                'timeframe': timeframe,
                'status': 'success',
                'created': created_count,
                'updated': updated_count,
                'total': len(order_blocks),
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(
                f"Order Block update completed: {created_count} created, "
                f"{updated_count} updated in {duration:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Error updating Order Blocks: {e}", exc_info=True)
            return {
                'timeframe': timeframe,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

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
