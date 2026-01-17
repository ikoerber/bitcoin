"""
Technical Indicators for Bitcoin Trading Analysis

Implements common technical indicators used in trading:
- RSI (Relative Strength Index)
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- Bollinger Bands

All calculations use pandas for efficient computation.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any


class TechnicalIndicators:
    """Calculate technical indicators for BTC/EUR data"""

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index (RSI).

        RSI measures the magnitude of recent price changes to evaluate
        overbought or oversold conditions.

        Args:
            df: DataFrame with 'close' column
            period: RSI period (default: 14)

        Returns:
            Series with RSI values (0-100)

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")

        if period <= 0:
            raise ValueError("Period must be positive")

        if len(df) < period:
            raise ValueError(f"Need at least {period} data points for RSI calculation (have {len(df)})")

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # Prevent division by zero: replace zero loss with NaN
        # When loss is 0, RSI should be 100 (all gains, no losses)
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # Handle edge case: when loss is 0 (all gains), RSI = 100
        rsi = rsi.fillna(100)

        return rsi

    @staticmethod
    def calculate_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Calculate Simple Moving Average (SMA).

        SMA smooths price data by calculating the average of prices
        over a specified period.

        Args:
            df: DataFrame with 'close' column
            period: SMA period (default: 20)

        Returns:
            Series with SMA values

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")

        if period <= 0:
            raise ValueError("Period must be positive")

        if len(df) < period:
            raise ValueError(f"Need at least {period} data points for SMA calculation (have {len(df)})")

        return df['close'].rolling(window=period).mean()

    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        Calculate Exponential Moving Average (EMA).

        EMA gives more weight to recent prices, making it more
        responsive to new information than SMA.

        Args:
            df: DataFrame with 'close' column
            period: EMA period (default: 20)

        Returns:
            Series with EMA values

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")

        if period <= 0:
            raise ValueError("Period must be positive")

        if len(df) < period:
            raise ValueError(f"Need at least {period} data points for EMA calculation (have {len(df)})")

        return df['close'].ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_bollinger_bands(
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.

        Bollinger Bands consist of a middle band (SMA) and upper/lower bands
        that are standard deviations away from the middle band.

        Args:
            df: DataFrame with 'close' column
            period: Period for moving average (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)

        Returns:
            Dictionary with 'upper', 'middle', 'lower' series

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        if 'close' not in df.columns:
            raise ValueError("DataFrame must have 'close' column")

        if period <= 0:
            raise ValueError("Period must be positive")

        if std_dev <= 0:
            raise ValueError("Standard deviation multiplier must be positive")

        if len(df) < period:
            raise ValueError(f"Need at least {period} data points for Bollinger Bands calculation (have {len(df)})")

        middle = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    @staticmethod
    def prepare_indicator_data(
        timestamps: pd.Series,
        values: pd.Series
    ) -> List[Dict[str, Any]]:
        """
        Convert indicator series to API-ready format.

        Args:
            timestamps: Timestamp series (milliseconds)
            values: Indicator values

        Returns:
            List of dicts with 'time' and 'value' keys (TradingView format)
        """
        result = []
        for ts, val in zip(timestamps, values):
            if pd.notna(val):  # Skip NaN values
                result.append({
                    'time': int(ts // 1000),  # Convert to seconds for TradingView
                    'value': float(val)
                })
        return result

    @staticmethod
    def prepare_bollinger_data(
        timestamps: pd.Series,
        bands: Dict[str, pd.Series]
    ) -> List[Dict[str, Any]]:
        """
        Convert Bollinger Bands to API-ready format.

        Args:
            timestamps: Timestamp series (milliseconds)
            bands: Dict with 'upper', 'middle', 'lower' series

        Returns:
            List of dicts with 'time', 'upper', 'middle', 'lower' keys
        """
        result = []
        for i, ts in enumerate(timestamps):
            # Only include if all three bands have valid values
            if all(pd.notna(bands[key].iloc[i]) for key in ['upper', 'middle', 'lower']):
                result.append({
                    'time': int(ts // 1000),  # Convert to seconds
                    'upper': float(bands['upper'].iloc[i]),
                    'middle': float(bands['middle'].iloc[i]),
                    'lower': float(bands['lower'].iloc[i])
                })
        return result

    @staticmethod
    def detect_engulfing_patterns(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Detect Bullish and Bearish Engulfing candlestick patterns.

        Bullish Engulfing:
        - Previous candle is bearish (red)
        - Current candle is bullish (green)
        - Current candle's body completely engulfs previous candle's body
        - Signal: Potential bullish reversal

        Bearish Engulfing:
        - Previous candle is bullish (green)
        - Current candle is bearish (red)
        - Current candle's body completely engulfs previous candle's body
        - Signal: Potential bearish reversal

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of engulfing patterns with time, type, and price levels
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame missing required columns: {missing_cols}")

        if len(df) < 2:
            raise ValueError("Need at least 2 data points for engulfing pattern detection")

        patterns = []

        for i in range(1, len(df)):
            prev = df.iloc[i-1]
            curr = df.iloc[i]

            # Determine candle types
            prev_is_bearish = prev['close'] < prev['open']
            prev_is_bullish = prev['close'] > prev['open']
            curr_is_bearish = curr['close'] < curr['open']
            curr_is_bullish = curr['close'] > curr['open']

            # Get body boundaries
            prev_body_top = max(prev['open'], prev['close'])
            prev_body_bottom = min(prev['open'], prev['close'])
            curr_body_top = max(curr['open'], curr['close'])
            curr_body_bottom = min(curr['open'], curr['close'])

            # Bullish Engulfing Pattern
            if prev_is_bearish and curr_is_bullish:
                # Check if current candle engulfs previous candle
                if curr_body_bottom < prev_body_bottom and curr_body_top > prev_body_top:
                    # Calculate pattern strength (how much bigger is the engulfing candle)
                    prev_body_size = abs(prev['close'] - prev['open'])
                    curr_body_size = abs(curr['close'] - curr['open'])
                    strength = (curr_body_size / prev_body_size) if prev_body_size > 0 else 1.0

                    pattern = {
                        'time': int(curr['timestamp'] // 1000),
                        'pattern_type': 'bullish_engulfing',
                        'prev_candle_time': int(prev['timestamp'] // 1000),
                        'price': float(curr['close']),
                        'low': float(curr['low']),
                        'high': float(curr['high']),
                        'strength': float(strength),
                        'prev_body_size': float(prev_body_size),
                        'curr_body_size': float(curr_body_size)
                    }
                    patterns.append(pattern)

            # Bearish Engulfing Pattern
            elif prev_is_bullish and curr_is_bearish:
                # Check if current candle engulfs previous candle
                if curr_body_bottom < prev_body_bottom and curr_body_top > prev_body_top:
                    # Calculate pattern strength
                    prev_body_size = abs(prev['close'] - prev['open'])
                    curr_body_size = abs(curr['close'] - curr['open'])
                    strength = (curr_body_size / prev_body_size) if prev_body_size > 0 else 1.0

                    pattern = {
                        'time': int(curr['timestamp'] // 1000),
                        'pattern_type': 'bearish_engulfing',
                        'prev_candle_time': int(prev['timestamp'] // 1000),
                        'price': float(curr['close']),
                        'low': float(curr['low']),
                        'high': float(curr['high']),
                        'strength': float(strength),
                        'prev_body_size': float(prev_body_size),
                        'curr_body_size': float(curr_body_size)
                    }
                    patterns.append(pattern)

        return patterns
