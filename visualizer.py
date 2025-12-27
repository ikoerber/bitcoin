"""
Bitcoin Trading Data Visualizer - BTC/EUR Candlestick Charts

This module provides visualization capabilities for Bitcoin market data stored in SQLite.
Generates interactive candlestick charts for all timeframes with volume analysis.

Author: Bitcoin Trading Data Application
License: MIT
"""

import sqlite3
import pandas as pd
import mplfinance as mpf
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
import os

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


class BTCVisualizer:
    """
    Visualizes Bitcoin (BTC/EUR) market data with candlestick charts.

    Features:
    - Multi-timeframe visualization (15m, 1h, 4h, 1d)
    - Candlestick charts with volume bars
    - Customizable date ranges
    - Automatic chart styling for professional analysis
    """

    # Timeframe configuration (must match db_manager.py)
    TIMEFRAMES = {
        '15m': 'btc_eur_15m',
        '1h': 'btc_eur_1h',
        '4h': 'btc_eur_4h',
        '1d': 'btc_eur_1d'
    }

    # Database configuration
    DB_NAME = 'btc_eur_data.db'

    # Chart style configuration
    CHART_STYLE = 'charles'  # Professional trading style
    CHART_TYPE = 'candle'

    def __init__(self, db_name: Optional[str] = None):
        """
        Initialize the BTC Visualizer.

        Args:
            db_name: Optional custom database name (defaults to btc_eur_data.db)
        """
        self.db_name = db_name or self.DB_NAME
        self._verify_database()

    def _verify_database(self) -> None:
        """Verify that the database exists and is accessible."""
        if not os.path.exists(self.db_name):
            error_msg = f"Database {self.db_name} not found. Please run db_manager.py first."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            conn = sqlite3.connect(self.db_name)
            conn.close()
            logger.info(f"Successfully connected to database {self.db_name}")
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _load_data(
        self,
        timeframe: str,
        days_back: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load OHLCV data from database for a specific timeframe.

        Args:
            timeframe: Timeframe to load (15m, 1h, 4h, 1d)
            days_back: Number of days to load (from most recent)
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with OHLCV data indexed by datetime
        """
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {list(self.TIMEFRAMES.keys())}")

        table_name = self.TIMEFRAMES[timeframe]

        try:
            conn = sqlite3.connect(self.db_name)

            # Build query with optional date filtering
            query = f"""
                SELECT datum, open, high, low, close, volume
                FROM {table_name}
            """

            conditions = []
            if start_date:
                conditions.append(f"datum >= '{start_date}'")
            if end_date:
                conditions.append(f"datum <= '{end_date}'")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY datum ASC"

            # Load data
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                logger.warning(f"No data found for {timeframe} timeframe with given filters")
                return df

            # Convert datum to datetime and set as index
            df['datum'] = pd.to_datetime(df['datum'])
            df.set_index('datum', inplace=True)

            # Apply days_back filter if specified
            if days_back:
                cutoff_date = df.index[-1] - timedelta(days=days_back)
                df = df[df.index >= cutoff_date]

            logger.info(f"Loaded {len(df)} candles for {timeframe} timeframe")
            return df

        except sqlite3.Error as e:
            logger.error(f"Database error loading {timeframe} data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {timeframe} data: {e}")
            raise

    def _get_chart_title(self, timeframe: str, df: pd.DataFrame) -> str:
        """
        Generate chart title with timeframe and date range info.

        Args:
            timeframe: Timeframe string
            df: DataFrame with the data

        Returns:
            Formatted title string
        """
        if df.empty:
            return f"BTC/EUR - {timeframe} - No Data"

        start_date = df.index[0].strftime('%Y-%m-%d %H:%M')
        end_date = df.index[-1].strftime('%Y-%m-%d %H:%M')
        num_candles = len(df)

        return f"BTC/EUR - {timeframe} ({num_candles} candles)\n{start_date} to {end_date}"

    def plot_timeframe(
        self,
        timeframe: str,
        days_back: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_path: Optional[str] = None,
        show: bool = True
    ) -> None:
        """
        Plot candlestick chart for a specific timeframe.

        Args:
            timeframe: Timeframe to plot (15m, 1h, 4h, 1d)
            days_back: Number of days to display (from most recent)
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            save_path: Optional path to save chart image
            show: Whether to display the chart (default: True)
        """
        logger.info(f"Generating chart for {timeframe} timeframe...")

        # Load data
        df = self._load_data(timeframe, days_back, start_date, end_date)

        if df.empty:
            print(f"\nNo data available for {timeframe} timeframe with given filters.")
            print("Please run db_manager.py to collect data first.")
            return

        # Prepare chart configuration
        title = self._get_chart_title(timeframe, df)

        # Market colors (green/red for up/down candles)
        mc = mpf.make_marketcolors(
            up='#26a69a',      # Green for bullish candles
            down='#ef5350',    # Red for bearish candles
            edge='inherit',
            wick='inherit',
            volume='in'
        )

        # Chart style
        style = mpf.make_mpf_style(
            marketcolors=mc,
            gridstyle='-',
            gridcolor='#e0e0e0',
            facecolor='white',
            figcolor='white',
            y_on_right=False
        )

        # Plot configuration
        kwargs = {
            'type': self.CHART_TYPE,
            'style': style,
            'title': title,
            'volume': True,
            'ylabel': 'Price (EUR)',
            'ylabel_lower': 'Volume',
            'figsize': (14, 8),
            'tight_layout': True
        }

        if save_path:
            kwargs['savefig'] = save_path
            logger.info(f"Saving chart to {save_path}")

        # Generate chart
        try:
            mpf.plot(df, **kwargs)
            if show:
                logger.info("Displaying chart...")
            else:
                logger.info("Chart saved successfully")
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise

    def plot_all_timeframes(
        self,
        days_back: Optional[int] = 30,
        save_dir: Optional[str] = None,
        show: bool = False
    ) -> None:
        """
        Generate charts for all timeframes.

        Args:
            days_back: Number of days to display for each timeframe
            save_dir: Directory to save charts (creates if doesn't exist)
            show: Whether to display charts interactively (default: False for batch mode)
        """
        logger.info("="*60)
        logger.info("Generating charts for all timeframes")
        logger.info("="*60)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            logger.info(f"Charts will be saved to {save_dir}/")

        for timeframe in self.TIMEFRAMES.keys():
            try:
                save_path = None
                if save_dir:
                    save_path = os.path.join(save_dir, f"btc_eur_{timeframe}.png")

                self.plot_timeframe(
                    timeframe=timeframe,
                    days_back=days_back,
                    save_path=save_path,
                    show=show
                )

                print(f"✓ {timeframe} chart generated")

            except Exception as e:
                logger.error(f"Failed to generate {timeframe} chart: {e}")
                print(f"✗ {timeframe} chart failed: {e}")

        logger.info("="*60)
        logger.info("Chart generation completed")
        logger.info("="*60)

    def get_latest_price(self, timeframe: str = '15m') -> Optional[Tuple[datetime, float]]:
        """
        Get the most recent closing price.

        Args:
            timeframe: Timeframe to query (default: 15m for most recent)

        Returns:
            Tuple of (datetime, close_price) or None if no data
        """
        try:
            conn = sqlite3.connect(self.db_name)
            table_name = self.TIMEFRAMES[timeframe]

            query = f"""
                SELECT datum, close
                FROM {table_name}
                ORDER BY timestamp DESC
                LIMIT 1
            """

            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchone()
            conn.close()

            if result:
                datum, close = result
                return (datetime.strptime(datum, '%Y-%m-%d %H:%M:%S'), close)

            return None

        except Exception as e:
            logger.error(f"Error getting latest price: {e}")
            return None

    def print_latest_prices(self) -> None:
        """Print the latest closing prices for all timeframes."""
        print("\n" + "="*80)
        print("LATEST BTC/EUR CLOSING PRICES")
        print("="*80)

        for timeframe in self.TIMEFRAMES.keys():
            result = self.get_latest_price(timeframe)
            if result:
                datum, price = result
                print(f"{timeframe:>4}: €{price:>10,.2f}  (as of {datum})")
            else:
                print(f"{timeframe:>4}: No data available")

        print("="*80 + "\n")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BITCOIN TRADING DATA VISUALIZER - BTC/EUR")
    print("="*80 + "\n")

    try:
        # Initialize visualizer
        visualizer = BTCVisualizer()

        # Print latest prices
        visualizer.print_latest_prices()

        # Interactive menu
        print("Select visualization mode:")
        print("  1. Display single timeframe (interactive)")
        print("  2. Generate all charts (save to files)")
        print("  3. Display all charts (interactive)")
        print("  4. Quick view - last 7 days, 1h timeframe")

        choice = input("\nEnter your choice (1-4) or press Enter for option 4: ").strip()

        if not choice:
            choice = '4'

        if choice == '1':
            print("\nAvailable timeframes: 15m, 1h, 4h, 1d")
            timeframe = input("Enter timeframe (default: 1h): ").strip() or '1h'
            days = input("Enter number of days to display (default: 30): ").strip()
            days_back = int(days) if days else 30

            visualizer.plot_timeframe(
                timeframe=timeframe,
                days_back=days_back,
                show=True
            )

        elif choice == '2':
            days = input("Enter number of days to display (default: 30): ").strip()
            days_back = int(days) if days else 30
            save_dir = input("Enter save directory (default: ./charts): ").strip() or './charts'

            visualizer.plot_all_timeframes(
                days_back=days_back,
                save_dir=save_dir,
                show=False
            )

            print(f"\nAll charts saved to {save_dir}/")

        elif choice == '3':
            days = input("Enter number of days to display (default: 30): ").strip()
            days_back = int(days) if days else 30

            print("\nNote: Charts will be displayed one at a time. Close each window to see the next.")
            visualizer.plot_all_timeframes(
                days_back=days_back,
                show=True
            )

        elif choice == '4':
            print("\nGenerating quick view: 1h timeframe, last 7 days...")
            visualizer.plot_timeframe(
                timeframe='1h',
                days_back=7,
                show=True
            )

        else:
            print("Invalid choice. Exiting.")
            return 1

    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nPlease run db_manager.py first to collect market data.")
        return 1
    except Exception as e:
        logger.error(f"Fatal error in visualizer: {e}")
        print(f"\nERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
