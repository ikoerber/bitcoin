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


class BTCEURTrade(models.Model):
    """
    Model for storing BTC/EUR trade history from Binance.

    This table stores all buy and sell orders for BTC/EUR pair,
    synchronized from Binance API via fetch_my_trades().
    """

    # Primary key: Binance trade ID (unique per trade)
    trade_id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Binance trade ID (unique identifier)"
    )

    # Order information
    order_id = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Binance order ID that this trade belongs to"
    )

    # Trade details
    symbol = models.CharField(
        max_length=20,
        default='BTC/EUR',
        help_text="Trading pair symbol"
    )

    timestamp = models.BigIntegerField(
        db_index=True,
        help_text="Trade execution timestamp (milliseconds since epoch)"
    )

    datetime = models.DateTimeField(
        db_index=True,
        help_text="Human-readable datetime of trade execution"
    )

    side = models.CharField(
        max_length=4,
        choices=[('buy', 'Buy'), ('sell', 'Sell')],
        db_index=True,
        help_text="Trade side: buy or sell"
    )

    # Price and amount
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Execution price in EUR per BTC"
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Amount of BTC traded"
    )

    cost = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Total cost in EUR (price * amount)"
    )

    # Fees
    fee_cost = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Fee amount paid"
    )

    fee_currency = models.CharField(
        max_length=10,
        help_text="Currency in which fee was paid (usually BNB)"
    )

    # Metadata
    is_maker = models.BooleanField(
        default=False,
        help_text="True if this was a maker order (provides liquidity)"
    )

    synced_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this trade was synced from Binance API"
    )

    class Meta:
        db_table = 'btc_eur_trades'
        ordering = ['-timestamp']  # Most recent first
        verbose_name = 'BTC/EUR Trade'
        verbose_name_plural = 'BTC/EUR Trades'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['side', '-timestamp']),
            models.Index(fields=['datetime']),
        ]

    def __str__(self):
        return f"{self.side.upper()} {self.amount} BTC @ €{self.price} on {self.datetime}"

    @property
    def datetime_str(self):
        """Human-readable datetime string"""
        return self.datetime.strftime('%Y-%m-%d %H:%M:%S')


class AssetTransaction(models.Model):
    """
    Model for storing asset transactions (deposits, transfers, converts).

    Tracks all asset movements including:
    - Deposits (fiat, crypto)
    - Transfers (internal Binance transfers)
    - Converts (crypto-to-crypto conversions)
    """

    # Transaction types
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('transfer', 'Transfer'),
        ('convert', 'Convert'),
    ]

    # Status choices
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]

    # Primary key: combination of type + Binance transaction ID
    transaction_id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique transaction identifier (type:id)"
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        db_index=True,
        help_text="Type of transaction"
    )

    timestamp = models.BigIntegerField(
        db_index=True,
        help_text="Transaction timestamp (milliseconds since epoch)"
    )

    datetime = models.DateTimeField(
        db_index=True,
        help_text="Human-readable datetime"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='success',
        help_text="Transaction status"
    )

    # Asset information
    currency = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Asset symbol (BTC, EUR, BNB, etc.)"
    )

    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Transaction amount"
    )

    # For converts: from/to currencies
    from_currency = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Source currency for converts"
    )

    to_currency = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Target currency for converts"
    )

    from_amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        null=True,
        blank=True,
        help_text="Source amount for converts"
    )

    # Fees
    fee = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Transaction fee"
    )

    fee_currency = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Fee currency"
    )

    # Additional metadata
    network = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Network used (for deposits/withdrawals)"
    )

    address = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Deposit/withdrawal address"
    )

    tx_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Blockchain transaction ID"
    )

    # Sync metadata
    synced_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this transaction was synced from Binance API"
    )

    class Meta:
        db_table = 'asset_transactions'
        ordering = ['-timestamp']
        verbose_name = 'Asset Transaction'
        verbose_name_plural = 'Asset Transactions'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['transaction_type', '-timestamp']),
            models.Index(fields=['currency', '-timestamp']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        if self.transaction_type == 'convert':
            return f"CONVERT {self.from_amount} {self.from_currency} → {self.amount} {self.to_currency} on {self.datetime}"
        return f"{self.transaction_type.upper()} {self.amount} {self.currency} on {self.datetime}"

    @property
    def datetime_str(self):
        """Human-readable datetime string"""
        return self.datetime.strftime('%Y-%m-%d %H:%M:%S')


class OpenOrder(models.Model):
    """
    Model for storing currently open limit orders from Binance.
    
    This table is refreshed on each sync to show current open orders.
    """
    
    # Order types
    ORDER_TYPES = [
        ('limit', 'Limit'),
        ('market', 'Market'),
        ('stop_loss', 'Stop Loss'),
        ('stop_loss_limit', 'Stop Loss Limit'),
    ]
    
    # Primary key: Binance order ID
    order_id = models.CharField(
        max_length=50,
        primary_key=True,
        help_text="Binance order ID"
    )
    
    symbol = models.CharField(
        max_length=20,
        default='BTC/EUR',
        db_index=True,
        help_text="Trading pair symbol"
    )
    
    timestamp = models.BigIntegerField(
        db_index=True,
        help_text="Order creation timestamp (milliseconds)"
    )
    
    datetime = models.DateTimeField(
        help_text="Human-readable datetime"
    )
    
    type = models.CharField(
        max_length=20,
        choices=ORDER_TYPES,
        help_text="Order type"
    )
    
    side = models.CharField(
        max_length=4,
        choices=[('buy', 'Buy'), ('sell', 'Sell')],
        db_index=True,
        help_text="Order side"
    )
    
    price = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Limit price"
    )
    
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Total order amount"
    )
    
    filled = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=0,
        help_text="Filled amount"
    )
    
    remaining = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Remaining amount to fill"
    )
    
    status = models.CharField(
        max_length=20,
        default='open',
        help_text="Order status"
    )
    
    synced_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this order was synced"
    )
    
    class Meta:
        db_table = 'open_orders'
        ordering = ['-timestamp']
        verbose_name = 'Open Order'
        verbose_name_plural = 'Open Orders'
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['side']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.side.upper()} {self.remaining}/{self.amount} BTC @ €{self.price}"

    @property
    def datetime_str(self):
        """Human-readable datetime string"""
        return self.datetime.strftime('%Y-%m-%d %H:%M:%S')


class OrderBlock1h(models.Model):
    """
    Model for storing Order Blocks detected on 1h timeframe.

    Order Blocks are institutional supply/demand zones identified using
    Smart Money Concepts (SMC) methodology with ATR-based displacement
    and Break of Structure (BOS) confirmation.

    Status lifecycle: fresh → touched → invalid
    """

    # Direction choices
    DIRECTION_CHOICES = [
        ('bullish', 'Bullish'),
        ('bearish', 'Bearish'),
    ]

    # Status choices
    STATUS_CHOICES = [
        ('fresh', 'Fresh'),
        ('touched', 'Touched'),
        ('invalid', 'Invalid'),
    ]

    # Primary key
    id = models.AutoField(primary_key=True)

    # Order Block metadata
    symbol = models.CharField(
        max_length=20,
        default='BTC/EUR',
        db_index=True,
        help_text="Trading pair symbol"
    )

    direction = models.CharField(
        max_length=8,
        choices=DIRECTION_CHOICES,
        db_index=True,
        help_text="Bullish (demand) or Bearish (supply)"
    )

    # Timestamps
    created_ts_ms = models.BigIntegerField(
        db_index=True,
        help_text="Timestamp when Order Block candle formed (milliseconds)"
    )

    valid_from_ts_ms = models.BigIntegerField(
        db_index=True,
        help_text="Timestamp when Order Block became valid"
    )

    valid_to_ts_ms = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Timestamp when Order Block was invalidated (null if still valid)"
    )

    # Price levels
    price_low = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Lower bound of Order Block zone (EUR)"
    )

    price_high = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Upper bound of Order Block zone (EUR)"
    )

    # Technical indicators
    atr14 = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="ATR(14) value at time of formation"
    )

    bos_level = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Break of Structure level that confirmed this Order Block"
    )

    displacement_range = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        help_text="Range of displacement candle (high - low)"
    )

    # Status tracking
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='fresh',
        db_index=True,
        help_text="Current status: fresh, touched, or invalid"
    )

    # Audit timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this record was created in database"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this record was last updated"
    )

    class Meta:
        db_table = 'order_blocks_1h'
        ordering = ['-created_ts_ms']
        verbose_name = 'Order Block (1h)'
        verbose_name_plural = 'Order Blocks (1h)'
        indexes = [
            models.Index(fields=['symbol', 'status', '-created_ts_ms'], name='idx_ob_symbol_status_ts'),
            models.Index(fields=['direction', 'status'], name='idx_ob_direction_status'),
            models.Index(fields=['valid_from_ts_ms', 'valid_to_ts_ms'], name='idx_ob_valid_time_range'),
        ]

    def __str__(self):
        return f"{self.direction.upper()} OB @ €{self.price_low:.2f}-{self.price_high:.2f} ({self.status})"

    @property
    def zone_size(self) -> float:
        """Calculate zone size in EUR."""
        return float(self.price_high - self.price_low)

    @property
    def is_valid(self) -> bool:
        """Check if Order Block is still valid (fresh or touched, not invalid)."""
        return self.status in ['fresh', 'touched']

    @property
    def created_datetime_str(self):
        """Human-readable datetime string for creation timestamp."""
        from datetime import datetime
        return datetime.fromtimestamp(self.created_ts_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
