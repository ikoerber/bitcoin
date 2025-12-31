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
    def detect_orderblocks(df: pd.DataFrame, min_move_percent: float = 1.0, lookback: int = 20) -> List[Dict[str, Any]]:
        """
        Detect Order Blocks using Smart Money Concepts (ICT) methodology.

        An Order Block is formed by:
        - Bullish OB: Last bearish (down) candle before a significant bullish move
        - Bearish OB: Last bullish (up) candle before a significant bearish move

        Args:
            df: DataFrame with OHLCV data
            min_move_percent: Minimum price move to confirm OB (default: 1.0%)
            lookback: Number of candles to check for valid move (default: 20)

        Returns:
            List of orderblocks with time, price levels, type, and mitigation status
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame missing required columns: {missing_cols}")

        if len(df) < lookback + 2:
            raise ValueError(f"Need at least {lookback + 2} data points for orderblock detection")

        orderblocks = []

        for i in range(len(df) - lookback):
            current = df.iloc[i]

            # Determine if current candle is bullish or bearish
            is_bearish_candle = current['close'] < current['open']
            is_bullish_candle = current['close'] > current['open']

            # Look ahead to check for significant move
            future_candles = df.iloc[i+1:i+1+lookback]

            if is_bearish_candle:
                # Check for bullish move after this bearish candle
                # (This bearish candle could be a bullish orderblock)
                highest_high = future_candles['high'].max()
                move_percent = ((highest_high - current['close']) / current['close']) * 100

                if move_percent >= min_move_percent:
                    ob = {
                        'start_time': int(current['timestamp'] // 1000),
                        'end_time': int(current['timestamp'] // 1000),  # Single candle
                        'ob_high': float(current['high']),
                        'ob_low': float(current['low']),
                        'ob_type': 'bullish',
                        'strength': float(move_percent),
                        'mitigated': False
                    }

                    # Check if orderblock has been mitigated (price returned to this zone)
                    for j in range(i + 1, len(df)):
                        future = df.iloc[j]
                        # Mitigation occurs when price returns to the orderblock zone
                        if future['low'] <= current['high'] and future['high'] >= current['low']:
                            ob['mitigated'] = True
                            ob['mitigation_time'] = int(future['timestamp'] // 1000)
                            break

                    orderblocks.append(ob)

            elif is_bullish_candle:
                # Check for bearish move after this bullish candle
                # (This bullish candle could be a bearish orderblock)
                lowest_low = future_candles['low'].min()
                move_percent = ((current['close'] - lowest_low) / current['close']) * 100

                if move_percent >= min_move_percent:
                    ob = {
                        'start_time': int(current['timestamp'] // 1000),
                        'end_time': int(current['timestamp'] // 1000),
                        'ob_high': float(current['high']),
                        'ob_low': float(current['low']),
                        'ob_type': 'bearish',
                        'strength': float(move_percent),
                        'mitigated': False
                    }

                    # Check if mitigated
                    for j in range(i + 1, len(df)):
                        future = df.iloc[j]
                        if future['low'] <= current['high'] and future['high'] >= current['low']:
                            ob['mitigated'] = True
                            ob['mitigation_time'] = int(future['timestamp'] // 1000)
                            break

                    orderblocks.append(ob)

        return orderblocks

    @staticmethod
    def detect_swing_points(df: pd.DataFrame, lookback: int = 5) -> List[Dict[str, Any]]:
        """
        Detect swing highs and swing lows using local extrema algorithm.

        A swing high is a candle whose high is the highest within lookback candles
        on both sides. A swing low is a candle whose low is the lowest within
        lookback candles on both sides.

        Args:
            df: DataFrame with OHLCV data
            lookback: Number of candles to check on each side (default: 5)

        Returns:
            List of swing points with time, price, type, and index

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        # Input validation
        if df.empty:
            raise ValueError("DataFrame is empty")

        required_cols = ['timestamp', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"DataFrame missing required columns: {missing_cols}")

        min_required = 2 * lookback + 1
        if len(df) < min_required:
            raise ValueError(f"Need at least {min_required} data points for swing detection (have {len(df)})")

        if lookback < 1:
            raise ValueError("Lookback must be at least 1")

        swing_points = []

        # Iterate through candles (skip edges where we can't look both directions)
        for i in range(lookback, len(df) - lookback):
            current = df.iloc[i]

            # Check for swing high
            left_highs = df.iloc[i-lookback:i]['high']
            right_highs = df.iloc[i+1:i+1+lookback]['high']

            if current['high'] > left_highs.max() and current['high'] > right_highs.max():
                swing_points.append({
                    'time': int(current['timestamp'] // 1000),
                    'price': float(current['high']),
                    'type': 'high',
                    'index': i
                })

            # Check for swing low
            left_lows = df.iloc[i-lookback:i]['low']
            right_lows = df.iloc[i+1:i+1+lookback]['low']

            if current['low'] < left_lows.min() and current['low'] < right_lows.min():
                swing_points.append({
                    'time': int(current['timestamp'] // 1000),
                    'price': float(current['low']),
                    'type': 'low',
                    'index': i
                })

        return swing_points

    @staticmethod
    def detect_trend(df: pd.DataFrame, lookback: int = 5, min_move_percent: float = 0.5) -> Dict[str, Any]:
        """
        Detect trend direction using Higher Highs/Higher Lows methodology.

        Analyzes swing points to determine:
        - Uptrend: Series of higher highs AND higher lows
        - Downtrend: Series of lower highs AND lower lows
        - Sideways: Mixed signals or insufficient data

        Args:
            df: DataFrame with OHLCV data
            lookback: Swing point lookback window (default: 5)
            min_move_percent: Minimum % move between swings (default: 0.5%)

        Returns:
            Dict with trend_type, trendline_points, swing_points, confidence, statistics

        Raises:
            ValueError: If DataFrame is invalid
        """
        # Get swing points
        swing_points = TechnicalIndicators.detect_swing_points(df, lookback)

        if len(swing_points) < 3:
            return {
                'trend_type': 'sideways',
                'reason': 'insufficient_swings',
                'trendline_points': [],
                'swing_points': swing_points,
                'swing_highs_count': 0,
                'swing_lows_count': 0,
                'higher_high_count': 0,
                'lower_high_count': 0,
                'higher_low_count': 0,
                'lower_low_count': 0,
                'confidence': 0.0
            }

        # Separate into highs and lows
        swing_highs = [sp for sp in swing_points if sp['type'] == 'high']
        swing_lows = [sp for sp in swing_points if sp['type'] == 'low']

        # Sort by time
        swing_highs.sort(key=lambda x: x['time'])
        swing_lows.sort(key=lambda x: x['time'])

        # Analyze highs for HH/LH pattern
        higher_high_count = 0
        lower_high_count = 0

        for i in range(1, len(swing_highs)):
            price_change_pct = ((swing_highs[i]['price'] - swing_highs[i-1]['price'])
                                / swing_highs[i-1]['price'] * 100)

            if abs(price_change_pct) >= min_move_percent:
                if price_change_pct > 0:
                    higher_high_count += 1
                else:
                    lower_high_count += 1

        # Analyze lows for HL/LL pattern
        higher_low_count = 0
        lower_low_count = 0

        for i in range(1, len(swing_lows)):
            price_change_pct = ((swing_lows[i]['price'] - swing_lows[i-1]['price'])
                                / swing_lows[i-1]['price'] * 100)

            if abs(price_change_pct) >= min_move_percent:
                if price_change_pct > 0:
                    higher_low_count += 1
                else:
                    lower_low_count += 1

        # Determine trend direction
        trend_type = 'sideways'
        trendline_points = []
        confidence = 0.0

        total_comparisons = (len(swing_highs) + len(swing_lows) - 2)

        # Uptrend: HH + HL dominant
        if higher_high_count > 0 and higher_low_count > 0:
            if higher_high_count >= lower_high_count and higher_low_count >= lower_low_count:
                trend_type = 'uptrend'
                if total_comparisons > 0:
                    confidence = (higher_high_count + higher_low_count) / total_comparisons

                # Draw trendline connecting swing lows (support line)
                if len(swing_lows) >= 2:
                    first_low = swing_lows[0]
                    last_low = swing_lows[-1]

                    trendline_points = [
                        {'time': first_low['time'], 'value': first_low['price']},
                        {'time': last_low['time'], 'value': last_low['price']}
                    ]

                    # Extend line into future by 10%
                    time_range = last_low['time'] - first_low['time']
                    if time_range > 0:
                        extension = int(time_range * 0.1)
                        slope = (last_low['price'] - first_low['price']) / time_range
                        extended_time = last_low['time'] + extension
                        extended_value = last_low['price'] + (slope * extension)

                        trendline_points.append({
                            'time': extended_time,
                            'value': float(extended_value)
                        })

        # Downtrend: LH + LL dominant
        elif lower_high_count > 0 and lower_low_count > 0:
            if lower_high_count >= higher_high_count and lower_low_count >= higher_low_count:
                trend_type = 'downtrend'
                if total_comparisons > 0:
                    confidence = (lower_high_count + lower_low_count) / total_comparisons

                # Draw trendline connecting swing highs (resistance line)
                if len(swing_highs) >= 2:
                    first_high = swing_highs[0]
                    last_high = swing_highs[-1]

                    trendline_points = [
                        {'time': first_high['time'], 'value': first_high['price']},
                        {'time': last_high['time'], 'value': last_high['price']}
                    ]

                    # Extend line into future by 10%
                    time_range = last_high['time'] - first_high['time']
                    if time_range > 0:
                        extension = int(time_range * 0.1)
                        slope = (last_high['price'] - first_high['price']) / time_range
                        extended_time = last_high['time'] + extension
                        extended_value = last_high['price'] + (slope * extension)

                        trendline_points.append({
                            'time': extended_time,
                            'value': float(extended_value)
                        })

        return {
            'trend_type': trend_type,
            'trendline_points': trendline_points,
            'swing_points': swing_points,
            'swing_highs_count': len(swing_highs),
            'swing_lows_count': len(swing_lows),
            'higher_high_count': higher_high_count,
            'lower_high_count': lower_high_count,
            'higher_low_count': higher_low_count,
            'lower_low_count': lower_low_count,
            'confidence': float(confidence)
        }

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
