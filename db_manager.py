"""
Bitcoin Trading Data Manager - BTC/EUR Market Data Collection

This module handles data collection from Binance exchange and storage in SQLite database.
Supports multi-timeframe data collection (15m, 1h, 4h, 1d) with incremental updates.

Author: Bitcoin Trading Data Application
License: MIT
"""

import sqlite3
import ccxt
import pandas as pd
from datetime import datetime
import logging
from typing import Optional, List, Tuple
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bitcoin_data.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BTCDataManager:
    """
    Manages Bitcoin (BTC/EUR) market data collection and storage.

    Features:
    - Multi-timeframe data collection (15m, 1h, 4h, 1d)
    - Incremental updates to minimize API calls
    - SQLite database storage with automatic schema creation
    - Duplicate prevention via timestamp primary keys
    """

    # Timeframe configuration
    TIMEFRAMES = {
        '15m': 'btc_eur_15m',
        '1h': 'btc_eur_1h',
        '4h': 'btc_eur_4h',
        '1d': 'btc_eur_1d'
    }

    # Market configuration
    SYMBOL = 'BTC/EUR'
    EXCHANGE = 'binance'

    # Database configuration
    DB_NAME = 'btc_eur_data.db'

    def __init__(self, db_name: Optional[str] = None):
        """
        Initialize the BTC Data Manager.

        Args:
            db_name: Optional custom database name (defaults to btc_eur_data.db)
        """
        self.db_name = db_name or self.DB_NAME
        self.exchange = None
        self._initialize_exchange()
        self._initialize_database()

    def _initialize_exchange(self) -> None:
        """Initialize connection to Binance exchange via ccxt."""
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,  # Respect Binance rate limits
                'options': {
                    'defaultType': 'spot',  # Spot trading (not futures)
                }
            })
            logger.info(f"Successfully connected to {self.EXCHANGE} exchange")
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise

    def _initialize_database(self) -> None:
        """Create database and tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            # Create table for each timeframe
            for timeframe, table_name in self.TIMEFRAMES.items():
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        timestamp INTEGER PRIMARY KEY,
                        open REAL NOT NULL,
                        high REAL NOT NULL,
                        low REAL NOT NULL,
                        close REAL NOT NULL,
                        volume REAL NOT NULL,
                        datum TEXT NOT NULL
                    )
                """)
                logger.info(f"Table {table_name} ready")

            conn.commit()
            conn.close()
            logger.info(f"Database {self.db_name} initialized successfully")

        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def _get_latest_timestamp(self, table_name: str) -> Optional[int]:
        """
        Get the latest timestamp from a specific table.

        Args:
            table_name: Name of the table to query

        Returns:
            Latest timestamp in milliseconds, or None if table is empty
        """
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(timestamp) FROM {table_name}")
            result = cursor.fetchone()[0]
            conn.close()
            return result
        except sqlite3.Error as e:
            logger.error(f"Error getting latest timestamp from {table_name}: {e}")
            return None

    def _fetch_ohlcv(self, timeframe: str, since: Optional[int] = None, limit: int = 1000) -> List[List]:
        """
        Fetch OHLCV data from Binance.

        Args:
            timeframe: Timeframe string (15m, 1h, 4h, 1d)
            since: Starting timestamp in milliseconds (None = fetch latest)
            limit: Maximum number of candles to fetch (default: 1000)

        Returns:
            List of OHLCV candles
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.SYMBOL,
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            logger.info(f"Fetched {len(ohlcv)} candles for {timeframe} timeframe")
            return ohlcv
        except ccxt.NetworkError as e:
            logger.error(f"Network error fetching {timeframe} data: {e}")
            raise
        except ccxt.ExchangeError as e:
            logger.error(f"Exchange error fetching {timeframe} data: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {timeframe} data: {e}")
            raise

    def _store_ohlcv(self, table_name: str, ohlcv_data: List[List]) -> int:
        """
        Store OHLCV data in database.

        Args:
            table_name: Target table name
            ohlcv_data: List of OHLCV candles [timestamp, open, high, low, close, volume]

        Returns:
            Number of new records inserted
        """
        if not ohlcv_data:
            return 0

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            inserted_count = 0
            for candle in ohlcv_data:
                timestamp, open_price, high, low, close, volume = candle
                datum = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

                try:
                    cursor.execute(f"""
                        INSERT INTO {table_name} (timestamp, open, high, low, close, volume, datum)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (timestamp, open_price, high, low, close, volume, datum))
                    inserted_count += 1
                except sqlite3.IntegrityError:
                    # Duplicate timestamp - skip (this is expected behavior)
                    continue

            conn.commit()
            conn.close()

            if inserted_count > 0:
                logger.info(f"Inserted {inserted_count} new records into {table_name}")
            else:
                logger.info(f"No new records to insert into {table_name} (all up to date)")

            return inserted_count

        except sqlite3.Error as e:
            logger.error(f"Error storing data in {table_name}: {e}")
            raise

    def update_timeframe(self, timeframe: str, initial_limit: int = 1000) -> int:
        """
        Update data for a specific timeframe.

        Args:
            timeframe: Timeframe to update (15m, 1h, 4h, 1d)
            initial_limit: Number of candles to fetch if table is empty

        Returns:
            Number of new records added
        """
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {list(self.TIMEFRAMES.keys())}")

        table_name = self.TIMEFRAMES[timeframe]
        logger.info(f"Updating {timeframe} timeframe data...")

        # Get latest timestamp from database
        latest_timestamp = self._get_latest_timestamp(table_name)

        if latest_timestamp:
            # Incremental update: fetch only new data
            logger.info(f"Latest data point: {datetime.fromtimestamp(latest_timestamp/1000)}")
            # Add 1ms to avoid duplicate
            since = latest_timestamp + 1
        else:
            # Initial load: fetch recent historical data
            logger.info(f"No existing data - performing initial load of {initial_limit} candles")
            since = None

        # Fetch data from Binance
        ohlcv_data = self._fetch_ohlcv(timeframe, since=since, limit=initial_limit)

        # Store in database
        inserted = self._store_ohlcv(table_name, ohlcv_data)

        return inserted

    def update_all_timeframes(self, initial_limit: int = 1000) -> dict:
        """
        Update all configured timeframes.

        Args:
            initial_limit: Number of candles to fetch for empty tables

        Returns:
            Dictionary with update statistics for each timeframe
        """
        logger.info("="*60)
        logger.info("Starting multi-timeframe data update")
        logger.info("="*60)

        results = {}

        for timeframe in self.TIMEFRAMES.keys():
            try:
                inserted = self.update_timeframe(timeframe, initial_limit)
                results[timeframe] = {
                    'status': 'success',
                    'inserted': inserted
                }
                # Small delay to respect rate limits
                time.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to update {timeframe}: {e}")
                results[timeframe] = {
                    'status': 'failed',
                    'error': str(e)
                }

        logger.info("="*60)
        logger.info("Multi-timeframe update completed")
        logger.info("="*60)

        return results

    def get_data_summary(self) -> dict:
        """
        Get summary statistics for all timeframes.

        Returns:
            Dictionary with record counts and date ranges for each timeframe
        """
        summary = {}

        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()

            for timeframe, table_name in self.TIMEFRAMES.items():
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as count,
                        MIN(datum) as earliest,
                        MAX(datum) as latest
                    FROM {table_name}
                """)
                count, earliest, latest = cursor.fetchone()

                summary[timeframe] = {
                    'table': table_name,
                    'records': count,
                    'earliest': earliest,
                    'latest': latest
                }

            conn.close()

        except sqlite3.Error as e:
            logger.error(f"Error getting data summary: {e}")

        return summary

    def print_summary(self) -> None:
        """Print a formatted summary of the database contents."""
        summary = self.get_data_summary()

        print("\n" + "="*80)
        print("BTC/EUR DATABASE SUMMARY")
        print("="*80)

        for timeframe, info in summary.items():
            print(f"\nTimeframe: {timeframe}")
            print(f"  Table:    {info['table']}")
            print(f"  Records:  {info['records']:,}")
            if info['records'] > 0:
                print(f"  Earliest: {info['earliest']}")
                print(f"  Latest:   {info['latest']}")
            else:
                print("  Status:   No data")

        print("\n" + "="*80)


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BITCOIN TRADING DATA MANAGER - BTC/EUR")
    print("="*80 + "\n")

    try:
        # Initialize data manager
        manager = BTCDataManager()

        # Update all timeframes
        results = manager.update_all_timeframes(initial_limit=1000)

        # Print results
        print("\n" + "-"*80)
        print("UPDATE RESULTS")
        print("-"*80)
        for timeframe, result in results.items():
            if result['status'] == 'success':
                print(f"{timeframe:>4}: ✓ {result['inserted']} new records")
            else:
                print(f"{timeframe:>4}: ✗ Failed - {result['error']}")

        # Print database summary
        manager.print_summary()

    except Exception as e:
        logger.error(f"Fatal error in main execution: {e}")
        print(f"\nERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
