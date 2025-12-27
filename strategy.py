"""
Bitcoin Trading Strategy Framework - BTC/EUR Technical Analysis

This module provides the foundation for technical analysis and signal generation.
Includes base structure for implementing indicators and trading strategies.

Author: Bitcoin Trading Data Application
License: MIT
"""

import sqlite3
import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
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


class TechnicalAnalyzer:
    """
    Framework for technical analysis of Bitcoin (BTC/EUR) market data.

    This class provides the infrastructure for:
    - Loading market data from database
    - Calculating technical indicators (to be implemented)
    - Generating trading signals (to be implemented)
    - Backtesting strategies (to be implemented)

    Future development areas:
    - RSI (Relative Strength Index)
    - Moving Averages (SMA, EMA)
    - Bollinger Bands
    - MACD (Moving Average Convergence Divergence)
    - Volume analysis
    - Pattern recognition
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

    def __init__(self, db_name: Optional[str] = None):
        """
        Initialize the Technical Analyzer.

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

    def load_data(
        self,
        timeframe: str,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load OHLCV data from database for analysis.

        Args:
            timeframe: Timeframe to load (15m, 1h, 4h, 1d)
            limit: Maximum number of most recent candles to load
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

            # Build query
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

            if limit:
                query += f" LIMIT {limit}"

            # Load data
            df = pd.read_sql_query(query, conn)
            conn.close()

            if df.empty:
                logger.warning(f"No data found for {timeframe} timeframe with given filters")
                return df

            # Convert datum to datetime and set as index
            df['datum'] = pd.to_datetime(df['datum'])
            df.set_index('datum', inplace=True)

            logger.info(f"Loaded {len(df)} candles for analysis ({timeframe} timeframe)")
            return df

        except sqlite3.Error as e:
            logger.error(f"Database error loading {timeframe} data: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading {timeframe} data: {e}")
            raise

    def calculate_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate price returns (percentage change).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with added 'returns' column
        """
        if df.empty:
            return df

        df = df.copy()
        df['returns'] = df['close'].pct_change() * 100  # Percentage
        logger.info("Calculated price returns")
        return df

    def calculate_volatility(self, df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Calculate rolling volatility (standard deviation of returns).

        Args:
            df: DataFrame with OHLCV data
            window: Rolling window size (default: 20 periods)

        Returns:
            DataFrame with added 'volatility' column
        """
        if df.empty:
            return df

        df = df.copy()

        # Calculate returns if not already present
        if 'returns' not in df.columns:
            df['returns'] = df['close'].pct_change() * 100

        # Calculate rolling volatility
        df['volatility'] = df['returns'].rolling(window=window).std()
        logger.info(f"Calculated {window}-period rolling volatility")
        return df

    def get_price_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate basic price statistics.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with statistical measures
        """
        if df.empty:
            return {}

        stats = {
            'count': len(df),
            'start_date': df.index[0].strftime('%Y-%m-%d %H:%M:%S'),
            'end_date': df.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            'open_price': float(df['open'].iloc[0]),
            'close_price': float(df['close'].iloc[-1]),
            'highest': float(df['high'].max()),
            'lowest': float(df['low'].min()),
            'average': float(df['close'].mean()),
            'median': float(df['close'].median()),
            'std_dev': float(df['close'].std()),
            'total_volume': float(df['volume'].sum()),
            'avg_volume': float(df['volume'].mean()),
        }

        # Calculate period return
        stats['period_return'] = ((stats['close_price'] - stats['open_price']) / stats['open_price']) * 100

        return stats

    def print_statistics(self, timeframe: str, limit: Optional[int] = None) -> None:
        """
        Load data and print statistical analysis.

        Args:
            timeframe: Timeframe to analyze
            limit: Number of recent candles to analyze (None = all)
        """
        logger.info(f"Analyzing {timeframe} timeframe statistics...")

        df = self.load_data(timeframe, limit=limit)

        if df.empty:
            print(f"\nNo data available for {timeframe} timeframe.")
            return

        stats = self.get_price_statistics(df)

        print("\n" + "="*80)
        print(f"BTC/EUR STATISTICAL ANALYSIS - {timeframe.upper()} TIMEFRAME")
        print("="*80)

        print(f"\nData Range:")
        print(f"  Period:       {stats['start_date']} to {stats['end_date']}")
        print(f"  Candles:      {stats['count']:,}")

        print(f"\nPrice Analysis:")
        print(f"  Opening:      €{stats['open_price']:>12,.2f}")
        print(f"  Closing:      €{stats['close_price']:>12,.2f}")
        print(f"  Period Return: {stats['period_return']:>11.2f}%")
        print(f"  Highest:      €{stats['highest']:>12,.2f}")
        print(f"  Lowest:       €{stats['lowest']:>12,.2f}")
        print(f"  Average:      €{stats['average']:>12,.2f}")
        print(f"  Median:       €{stats['median']:>12,.2f}")
        print(f"  Std Dev:      €{stats['std_dev']:>12,.2f}")

        print(f"\nVolume Analysis:")
        print(f"  Total Volume:  {stats['total_volume']:>12,.2f} BTC")
        print(f"  Avg Volume:    {stats['avg_volume']:>12,.2f} BTC")

        print("="*80 + "\n")

    def analyze_all_timeframes(self, days_back: int = 30) -> None:
        """
        Perform statistical analysis on all timeframes.

        Args:
            days_back: Number of days to analyze
        """
        print("\n" + "="*80)
        print(f"MULTI-TIMEFRAME ANALYSIS - LAST {days_back} DAYS")
        print("="*80)

        for timeframe in self.TIMEFRAMES.keys():
            try:
                self.print_statistics(timeframe, limit=None)
            except Exception as e:
                logger.error(f"Failed to analyze {timeframe}: {e}")
                print(f"\n✗ {timeframe} analysis failed: {e}\n")

    def detect_simple_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect basic price patterns (foundation for future pattern recognition).

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with pattern detection columns
        """
        if df.empty or len(df) < 3:
            return df

        df = df.copy()

        # Bullish/Bearish candles
        df['bullish'] = df['close'] > df['open']
        df['bearish'] = df['close'] < df['open']

        # Candle body size (as percentage of price)
        df['body_size'] = abs(df['close'] - df['open']) / df['open'] * 100

        # Upper and lower wicks
        df['upper_wick'] = np.where(
            df['bullish'],
            df['high'] - df['close'],
            df['high'] - df['open']
        )
        df['lower_wick'] = np.where(
            df['bullish'],
            df['open'] - df['low'],
            df['close'] - df['low']
        )

        # Doji detection (small body relative to wicks)
        avg_body = df['body_size'].mean()
        df['is_doji'] = df['body_size'] < (avg_body * 0.1)

        logger.info("Detected basic candlestick patterns")
        return df

    def get_market_overview(self, timeframe: str = '1h', periods: int = 100) -> None:
        """
        Print a comprehensive market overview.

        Args:
            timeframe: Timeframe to analyze (default: 1h)
            periods: Number of recent periods to analyze
        """
        logger.info(f"Generating market overview for {timeframe} timeframe...")

        df = self.load_data(timeframe, limit=periods)

        if df.empty:
            print(f"\nNo data available for {timeframe} timeframe.")
            return

        # Calculate indicators
        df = self.calculate_returns(df)
        df = self.calculate_volatility(df, window=20)
        df = self.detect_simple_patterns(df)

        # Get latest candle
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else None

        print("\n" + "="*80)
        print(f"BTC/EUR MARKET OVERVIEW - {timeframe.upper()} TIMEFRAME")
        print("="*80)

        print(f"\nLatest Candle ({latest.name}):")
        print(f"  Open:         €{latest['open']:>10,.2f}")
        print(f"  High:         €{latest['high']:>10,.2f}")
        print(f"  Low:          €{latest['low']:>10,.2f}")
        print(f"  Close:        €{latest['close']:>10,.2f}")
        print(f"  Volume:        {latest['volume']:>10,.4f} BTC")

        if prev is not None:
            change = latest['close'] - prev['close']
            change_pct = (change / prev['close']) * 100
            direction = "↑" if change > 0 else "↓"
            print(f"  Change:       {direction} €{abs(change):>9,.2f} ({change_pct:+.2f}%)")

        candle_type = "BULLISH 📈" if latest['bullish'] else "BEARISH 📉"
        print(f"  Type:          {candle_type}")

        if latest['is_doji']:
            print(f"  Pattern:       DOJI (Indecision)")

        # Recent statistics
        recent_stats = {
            'avg_volume': df['volume'].tail(20).mean(),
            'avg_volatility': df['volatility'].tail(20).mean(),
            'bullish_count': df['bullish'].tail(20).sum(),
            'bearish_count': df['bearish'].tail(20).sum(),
        }

        print(f"\nRecent Trends (Last 20 Candles):")
        print(f"  Bullish candles:  {recent_stats['bullish_count']}")
        print(f"  Bearish candles:  {recent_stats['bearish_count']}")
        print(f"  Avg volatility:   {recent_stats['avg_volatility']:.2f}%")
        print(f"  Avg volume:       {recent_stats['avg_volume']:.4f} BTC")

        print("="*80 + "\n")


def main():
    """Main execution function."""
    print("\n" + "="*80)
    print("BITCOIN TRADING STRATEGY FRAMEWORK - BTC/EUR")
    print("="*80 + "\n")

    try:
        # Initialize analyzer
        analyzer = TechnicalAnalyzer()

        # Interactive menu
        print("Select analysis mode:")
        print("  1. Market overview (1h timeframe, last 100 periods)")
        print("  2. Statistical analysis (single timeframe)")
        print("  3. Multi-timeframe analysis (all timeframes)")
        print("  4. Custom analysis")

        choice = input("\nEnter your choice (1-4) or press Enter for option 1: ").strip()

        if not choice:
            choice = '1'

        if choice == '1':
            analyzer.get_market_overview(timeframe='1h', periods=100)

        elif choice == '2':
            print("\nAvailable timeframes: 15m, 1h, 4h, 1d")
            timeframe = input("Enter timeframe (default: 1h): ").strip() or '1h'
            analyzer.print_statistics(timeframe)

        elif choice == '3':
            days = input("Enter number of days to analyze (default: 30): ").strip()
            days_back = int(days) if days else 30
            analyzer.analyze_all_timeframes(days_back=days_back)

        elif choice == '4':
            print("\nAvailable timeframes: 15m, 1h, 4h, 1d")
            timeframe = input("Enter timeframe: ").strip() or '1h'
            periods = input("Enter number of periods (default: all): ").strip()
            limit = int(periods) if periods else None

            df = analyzer.load_data(timeframe, limit=limit)
            if not df.empty:
                df = analyzer.calculate_returns(df)
                df = analyzer.calculate_volatility(df)
                df = analyzer.detect_simple_patterns(df)

                print(f"\nLoaded {len(df)} candles")
                print("\nDataFrame columns:", df.columns.tolist())
                print("\nFirst 5 rows:")
                print(df.head())
                print("\nLast 5 rows:")
                print(df.tail())

                stats = analyzer.get_price_statistics(df)
                print(f"\nPeriod return: {stats['period_return']:.2f}%")

        else:
            print("Invalid choice. Exiting.")
            return 1

    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nPlease run db_manager.py first to collect market data.")
        return 1
    except Exception as e:
        logger.error(f"Fatal error in strategy analyzer: {e}")
        print(f"\nERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
