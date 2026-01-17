"""
Order Block Analytics Engine

Implements Smart Money Concepts (SMC) based Order Block detection using:
- ATR(14) with Wilder's smoothing for displacement detection
- Fractal swing points (N=3 window) for structure identification
- Break of Structure (BOS) confirmation
- Mitigation tracking (fresh → touched → invalid lifecycle)

Algorithm based on orderblockspec.md specification with k=1.2 ATR multiplier.
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OrderBlockAnalyzer:
    """
    Analyze OHLCV data to detect Order Blocks using Smart Money Concepts.

    Order Blocks represent institutional supply/demand zones where smart money
    initiated positions, creating imbalances that price tends to return to.
    """

    def __init__(
        self,
        atr_period: int = 14,
        atr_multiplier: float = 1.2,
        swing_window: int = 3,
        zone_mode: str = 'conservative',
        min_candles: int = 200
    ):
        """
        Initialize Order Block Analyzer.

        Args:
            atr_period: Period for ATR calculation (default: 14)
            atr_multiplier: Multiplier for displacement detection (default: 1.2)
            swing_window: Window size for fractal swing detection (default: 3)
            zone_mode: 'conservative' (Open-Low/High-Open) or 'aggressive' (High-Low)
            min_candles: Minimum candles required for analysis (default: 200)
        """
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.swing_window = swing_window
        self.zone_mode = zone_mode
        self.min_candles = min_candles

        logger.info(
            f"OrderBlockAnalyzer initialized: ATR={atr_period}, k={atr_multiplier}, "
            f"swing_window={swing_window}, zone_mode={zone_mode}"
        )

    def analyze(self, df: pd.DataFrame) -> List[Dict]:
        """
        Main analysis pipeline: detect Order Blocks from OHLCV data.

        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume

        Returns:
            List of Order Block dictionaries with:
            - direction: 'bullish' or 'bearish'
            - created_ts_ms: Timestamp of OB candle
            - price_low: Lower bound of zone
            - price_high: Upper bound of zone
            - atr14: ATR value at formation
            - bos_level: BOS price level
            - displacement_range: Range of displacement candle
            - status: 'fresh', 'touched', or 'invalid'
        """
        # Validate input
        if df.empty or len(df) < self.min_candles:
            logger.warning(f"Insufficient data: {len(df)} candles (need {self.min_candles})")
            return []

        logger.info(f"Analyzing {len(df)} candles for Order Blocks")

        # Step 1: Calculate ATR(14)
        atr = self.calculate_atr(df)

        # Step 2: Detect swing points (Fractal N=3)
        swing_highs, swing_lows = self.detect_swing_points(df)
        logger.info(f"Detected {len(swing_highs)} swing highs, {len(swing_lows)} swing lows")

        # Step 3: Detect displacement candles
        displacement = self.detect_displacement(df, atr)
        logger.info(f"Detected {displacement.sum()} displacement candles")

        # Step 4: Detect Break of Structure
        bos_bullish, bos_bearish = self.detect_bos(df, swing_highs, swing_lows)
        logger.info(f"Detected {bos_bullish.sum()} bullish BOS, {bos_bearish.sum()} bearish BOS")

        # Step 5: Identify Order Blocks
        order_blocks = self.identify_order_blocks(
            df, displacement, bos_bullish, bos_bearish, atr, swing_highs, swing_lows
        )
        logger.info(f"Identified {len(order_blocks)} Order Blocks")

        # Step 6: Track mitigation
        order_blocks = self.track_mitigation(order_blocks, df)

        return order_blocks

    def calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate ATR(14) using Wilder's smoothing method.

        True Range = max(high - low, |high - prev_close|, |low - prev_close|)
        ATR = Exponential weighted mean with alpha = 1/period (Wilder's method)

        Args:
            df: DataFrame with high, low, close columns

        Returns:
            Series with ATR values
        """
        # Calculate True Range
        prev_close = df['close'].shift(1)

        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - prev_close).abs()
        tr3 = (df['low'] - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Calculate ATR using Wilder's smoothing (EWM with alpha=1/period)
        atr = true_range.ewm(alpha=1/self.atr_period, adjust=False).mean()

        return atr

    def detect_swing_points(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect fractal swing points using N=3 window.

        Swing High: High[i] = max(High[i-3...i+3])
        Swing Low: Low[i] = min(Low[i-3...i+3])

        Args:
            df: DataFrame with high, low, timestamp columns

        Returns:
            Tuple of (swing_highs, swing_lows) lists with {index, level, timestamp}
        """
        swing_highs = []
        swing_lows = []

        window = self.swing_window

        for i in range(window, len(df) - window):
            # Get window around current candle
            high_window = df['high'].iloc[i-window:i+window+1]
            low_window = df['low'].iloc[i-window:i+window+1]

            # Check if current candle is swing high
            if df['high'].iloc[i] == high_window.max():
                swing_highs.append({
                    'index': i,
                    'level': df['high'].iloc[i],
                    'timestamp': int(df['timestamp'].iloc[i])
                })

            # Check if current candle is swing low
            if df['low'].iloc[i] == low_window.min():
                swing_lows.append({
                    'index': i,
                    'level': df['low'].iloc[i],
                    'timestamp': int(df['timestamp'].iloc[i])
                })

        return swing_highs, swing_lows

    def detect_displacement(self, df: pd.DataFrame, atr: pd.Series) -> pd.Series:
        """
        Detect displacement candles where range >= k * ATR.

        Displacement indicates strong directional move (institutional activity).

        Args:
            df: DataFrame with high, low columns
            atr: Series with ATR values

        Returns:
            Boolean Series indicating displacement candles
        """
        candle_range = df['high'] - df['low']
        displacement_threshold = self.atr_multiplier * atr

        displacement = candle_range >= displacement_threshold

        return displacement

    def detect_bos(
        self,
        df: pd.DataFrame,
        swing_highs: List[Dict],
        swing_lows: List[Dict]
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Detect Break of Structure (BOS).

        Bullish BOS: Close breaks above last swing high
        Bearish BOS: Close breaks below last swing low

        Args:
            df: DataFrame with close column
            swing_highs: List of swing high dictionaries
            swing_lows: List of swing low dictionaries

        Returns:
            Tuple of (bos_bullish, bos_bearish) boolean Series
        """
        bos_bullish = pd.Series(False, index=df.index)
        bos_bearish = pd.Series(False, index=df.index)

        # Track last swing levels
        last_swing_high = None
        last_swing_low = None

        swing_high_idx = 0
        swing_low_idx = 0

        for i in range(len(df)):
            # Update last swing high if we passed one
            while swing_high_idx < len(swing_highs) and swing_highs[swing_high_idx]['index'] <= i:
                last_swing_high = swing_highs[swing_high_idx]['level']
                swing_high_idx += 1

            # Update last swing low if we passed one
            while swing_low_idx < len(swing_lows) and swing_lows[swing_low_idx]['index'] <= i:
                last_swing_low = swing_lows[swing_low_idx]['level']
                swing_low_idx += 1

            # Check for Bullish BOS (close above last swing high)
            if last_swing_high is not None and df['close'].iloc[i] > last_swing_high:
                bos_bullish.iloc[i] = True

            # Check for Bearish BOS (close below last swing low)
            if last_swing_low is not None and df['close'].iloc[i] < last_swing_low:
                bos_bearish.iloc[i] = True

        return bos_bullish, bos_bearish

    def identify_order_blocks(
        self,
        df: pd.DataFrame,
        displacement: pd.Series,
        bos_bullish: pd.Series,
        bos_bearish: pd.Series,
        atr: pd.Series,
        swing_highs: List[Dict],
        swing_lows: List[Dict]
    ) -> List[Dict]:
        """
        Identify Order Blocks based on displacement + BOS.

        Bullish OB: Last bearish candle before displacement-up that leads to BOS-up
        Bearish OB: Last bullish candle before displacement-down that leads to BOS-down

        Args:
            df: DataFrame with OHLCV data
            displacement: Boolean Series of displacement candles
            bos_bullish: Boolean Series of bullish BOS
            bos_bearish: Boolean Series of bearish BOS
            atr: Series with ATR values
            swing_highs: List of swing high dictionaries
            swing_lows: List of swing low dictionaries

        Returns:
            List of Order Block dictionaries
        """
        order_blocks = []

        # Find BOS events
        bullish_bos_indices = df[bos_bullish].index.tolist()
        bearish_bos_indices = df[bos_bearish].index.tolist()

        # Process Bullish Order Blocks (Demand zones)
        for bos_idx in bullish_bos_indices:
            # Find last displacement before BOS
            displacement_before = displacement[:bos_idx]

            if not displacement_before.any():
                continue

            last_displacement_idx = displacement_before[displacement_before].index[-1]

            # Find last bearish candle before displacement
            # (Bearish: close < open)
            bearish_candles = df[:last_displacement_idx][df['close'] < df['open']]

            if len(bearish_candles) == 0:
                continue

            ob_idx = bearish_candles.index[-1]
            ob_candle = df.loc[ob_idx]

            # Define zone (conservative: Open-Low, aggressive: High-Low)
            if self.zone_mode == 'conservative':
                price_low = min(ob_candle['open'], ob_candle['close'])
                price_high = max(ob_candle['open'], ob_candle['close'])
            else:  # aggressive
                price_low = ob_candle['low']
                price_high = ob_candle['high']

            # Get BOS level (last swing high that was broken)
            bos_swing = next((sh for sh in reversed(swing_highs) if sh['index'] < bos_idx), None)
            bos_level = bos_swing['level'] if bos_swing else df.loc[bos_idx, 'close']

            order_blocks.append({
                'direction': 'bullish',
                'created_ts_ms': int(ob_candle['timestamp']),
                'valid_from_ts_ms': int(ob_candle['timestamp']),
                'valid_to_ts_ms': None,
                'price_low': float(price_low),
                'price_high': float(price_high),
                'atr14': float(atr.loc[ob_idx]),
                'bos_level': float(bos_level),
                'displacement_range': float(df.loc[last_displacement_idx, 'high'] - df.loc[last_displacement_idx, 'low']),
                'status': 'fresh'
            })

        # Process Bearish Order Blocks (Supply zones)
        for bos_idx in bearish_bos_indices:
            # Find last displacement before BOS
            displacement_before = displacement[:bos_idx]

            if not displacement_before.any():
                continue

            last_displacement_idx = displacement_before[displacement_before].index[-1]

            # Find last bullish candle before displacement
            # (Bullish: close > open)
            bullish_candles = df[:last_displacement_idx][df['close'] > df['open']]

            if len(bullish_candles) == 0:
                continue

            ob_idx = bullish_candles.index[-1]
            ob_candle = df.loc[ob_idx]

            # Define zone (conservative: High-Open, aggressive: High-Low)
            if self.zone_mode == 'conservative':
                price_low = min(ob_candle['open'], ob_candle['close'])
                price_high = max(ob_candle['open'], ob_candle['close'])
            else:  # aggressive
                price_low = ob_candle['low']
                price_high = ob_candle['high']

            # Get BOS level (last swing low that was broken)
            bos_swing = next((sl for sl in reversed(swing_lows) if sl['index'] < bos_idx), None)
            bos_level = bos_swing['level'] if bos_swing else df.loc[bos_idx, 'close']

            order_blocks.append({
                'direction': 'bearish',
                'created_ts_ms': int(ob_candle['timestamp']),
                'valid_from_ts_ms': int(ob_candle['timestamp']),
                'valid_to_ts_ms': None,
                'price_low': float(price_low),
                'price_high': float(price_high),
                'atr14': float(atr.loc[ob_idx]),
                'bos_level': float(bos_level),
                'displacement_range': float(df.loc[last_displacement_idx, 'high'] - df.loc[last_displacement_idx, 'low']),
                'status': 'fresh'
            })

        return order_blocks

    def track_mitigation(self, order_blocks: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """
        Update Order Block status based on price action after formation.

        Status transitions:
        - fresh: Price has not touched the zone
        - touched: Price entered the zone (low <= zone_high AND high >= zone_low)
        - invalid: Price closed through the zone
            - Bullish OB: close < price_low
            - Bearish OB: close > price_high

        Args:
            order_blocks: List of Order Block dictionaries
            df: DataFrame with OHLCV data

        Returns:
            Updated list of Order Blocks with current status
        """
        for ob in order_blocks:
            created_ts = ob['created_ts_ms']
            price_low = ob['price_low']
            price_high = ob['price_high']
            direction = ob['direction']

            # Get candles after OB formation
            future_candles = df[df['timestamp'] > created_ts]

            if len(future_candles) == 0:
                continue

            # Check each future candle for mitigation
            for idx, candle in future_candles.iterrows():
                candle_low = candle['low']
                candle_high = candle['high']
                candle_close = candle['close']

                # Check if price touched the zone
                if candle_low <= price_high and candle_high >= price_low:
                    if ob['status'] == 'fresh':
                        ob['status'] = 'touched'

                # Check if price invalidated the zone
                if direction == 'bullish':
                    # Bullish OB invalid if close below zone
                    if candle_close < price_low:
                        ob['status'] = 'invalid'
                        ob['valid_to_ts_ms'] = int(candle['timestamp'])
                        break
                else:  # bearish
                    # Bearish OB invalid if close above zone
                    if candle_close > price_high:
                        ob['status'] = 'invalid'
                        ob['valid_to_ts_ms'] = int(candle['timestamp'])
                        break

        return order_blocks
