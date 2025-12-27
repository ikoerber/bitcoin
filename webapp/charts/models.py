"""
Django Models for Bitcoin Trading Data

These models map to existing SQLite database tables created by db_manager.py.
Using managed=False to prevent Django migrations from modifying the existing database.
"""

from django.db import models


class BTCEURBase(models.Model):
    """
    Abstract base model for BTC/EUR OHLCV data across all timeframes.

    This model defines the common structure shared by all timeframe tables:
    - btc_eur_15m (15-minute candles)
    - btc_eur_1h (1-hour candles)
    - btc_eur_4h (4-hour candles)
    - btc_eur_1d (1-day candles)
    """

    timestamp = models.BigIntegerField(primary_key=True, help_text="Unix timestamp in milliseconds")
    open = models.FloatField(help_text="Opening price in EUR")
    high = models.FloatField(help_text="Highest price in period (EUR)")
    low = models.FloatField(help_text="Lowest price in period (EUR)")
    close = models.FloatField(help_text="Closing price in EUR")
    volume = models.FloatField(help_text="Trading volume in BTC")
    datum = models.TextField(help_text="Human-readable datetime (YYYY-MM-DD HH:MM:SS)")

    class Meta:
        abstract = True
        managed = False  # CRITICAL: Don't let Django manage this table
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.datum} - Close: €{self.close:,.2f}"


class BTCEUR15m(BTCEURBase):
    """15-minute candle data for BTC/EUR"""

    class Meta(BTCEURBase.Meta):
        db_table = 'btc_eur_15m'
        verbose_name = 'BTC/EUR 15-Minute Candle'
        verbose_name_plural = 'BTC/EUR 15-Minute Candles'


class BTCEUR1h(BTCEURBase):
    """1-hour candle data for BTC/EUR"""

    class Meta(BTCEURBase.Meta):
        db_table = 'btc_eur_1h'
        verbose_name = 'BTC/EUR 1-Hour Candle'
        verbose_name_plural = 'BTC/EUR 1-Hour Candles'


class BTCEUR4h(BTCEURBase):
    """4-hour candle data for BTC/EUR"""

    class Meta(BTCEURBase.Meta):
        db_table = 'btc_eur_4h'
        verbose_name = 'BTC/EUR 4-Hour Candle'
        verbose_name_plural = 'BTC/EUR 4-Hour Candles'


class BTCEUR1d(BTCEURBase):
    """1-day candle data for BTC/EUR"""

    class Meta(BTCEURBase.Meta):
        db_table = 'btc_eur_1d'
        verbose_name = 'BTC/EUR 1-Day Candle'
        verbose_name_plural = 'BTC/EUR 1-Day Candles'


# Helper dictionary for timeframe-to-model mapping
TIMEFRAME_MODELS = {
    '15m': BTCEUR15m,
    '1h': BTCEUR1h,
    '4h': BTCEUR4h,
    '1d': BTCEUR1d,
}


def get_model_for_timeframe(timeframe: str):
    """
    Get Django model for a given timeframe string.

    Args:
        timeframe: Timeframe identifier ('15m', '1h', '4h', '1d')

    Returns:
        Django model class for the timeframe

    Raises:
        ValueError: If timeframe is invalid
    """
    if timeframe not in TIMEFRAME_MODELS:
        raise ValueError(
            f"Invalid timeframe: {timeframe}. "
            f"Must be one of {list(TIMEFRAME_MODELS.keys())}"
        )
    return TIMEFRAME_MODELS[timeframe]
