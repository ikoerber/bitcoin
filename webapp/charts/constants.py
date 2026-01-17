"""
Centralized constants for the charts application.

All magic numbers, configuration values, and repeated constants
are defined here to eliminate duplication across the codebase.
"""

# ============================================================================
# QUERY LIMITS
# ============================================================================

# Maximum number of records that can be queried from database
MAX_QUERY_LIMIT = 10000

# Default number of records to return if not specified
DEFAULT_LIMIT = 500

# Default number of days for time-based queries
DEFAULT_DAYS = 90

# Minimum and maximum days for queries
MIN_DAYS = 1
MAX_DAYS = 365


# ============================================================================
# TECHNICAL INDICATOR DEFAULTS
# ============================================================================

# Default period for RSI indicator
RSI_DEFAULT_PERIOD = 14

# Default period for moving averages (SMA, EMA)
MA_DEFAULT_PERIOD = 20

# Default period for Bollinger Bands
BB_DEFAULT_PERIOD = 20

# Default standard deviation for Bollinger Bands
BB_DEFAULT_STD_DEV = 2.0

# Minimum and maximum periods for indicators
MIN_INDICATOR_PERIOD = 1
MAX_INDICATOR_PERIOD = 200


# ============================================================================
# TIMEFRAMES
# ============================================================================

# Valid timeframes for OHLCV data
VALID_TIMEFRAMES = ['15m', '1h', '4h', '1d']

# Timeframe to database table name mapping
# Used by db_manager.py and other backend code
TIMEFRAME_TABLE_NAMES = {
    '15m': 'btc_eur_15m',
    '1h': 'btc_eur_1h',
    '4h': 'btc_eur_4h',
    '1d': 'btc_eur_1d'
}

# Timeframe display names (human-readable)
TIMEFRAME_DISPLAY_NAMES = {
    '15m': '15 Minutes',
    '1h': '1 Hour',
    '4h': '4 Hours',
    '1d': '1 Day'
}


# ============================================================================
# TRADING SYMBOLS
# ============================================================================

# Default trading pair
DEFAULT_SYMBOL = 'BTC/EUR'

# Supported trading pairs
SUPPORTED_SYMBOLS = ['BTC/EUR']


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

# Valid indicator types
VALID_INDICATORS = ['rsi', 'sma', 'ema', 'bb']

# Indicator display names
INDICATOR_DISPLAY_NAMES = {
    'rsi': 'Relative Strength Index',
    'sma': 'Simple Moving Average',
    'ema': 'Exponential Moving Average',
    'bb': 'Bollinger Bands'
}


# ============================================================================
# TRANSACTION TYPES
# ============================================================================

# Asset transaction types
TRANSACTION_TYPE_DEPOSIT = 'deposit'
TRANSACTION_TYPE_WITHDRAWAL = 'withdrawal'
TRANSACTION_TYPE_CONVERT = 'convert'
TRANSACTION_TYPE_TRANSFER = 'transfer'
TRANSACTION_TYPE_FIAT_DEPOSIT = 'fiat_deposit'
TRANSACTION_TYPE_FIAT_WITHDRAWAL = 'fiat_withdrawal'

# All valid transaction types
VALID_TRANSACTION_TYPES = [
    TRANSACTION_TYPE_DEPOSIT,
    TRANSACTION_TYPE_WITHDRAWAL,
    TRANSACTION_TYPE_CONVERT,
    TRANSACTION_TYPE_TRANSFER,
    TRANSACTION_TYPE_FIAT_DEPOSIT,
    TRANSACTION_TYPE_FIAT_WITHDRAWAL
]


# ============================================================================
# CURRENCIES
# ============================================================================

# Main currencies tracked in the system
CURRENCY_BTC = 'BTC'
CURRENCY_EUR = 'EUR'
CURRENCY_BNB = 'BNB'

# All tracked currencies
TRACKED_CURRENCIES = [CURRENCY_BTC, CURRENCY_EUR, CURRENCY_BNB]


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

# Default database filename
DEFAULT_DB_NAME = 'btc_eur_data.db'

# SQLite timeout in seconds
DB_TIMEOUT_SECONDS = 30


# ============================================================================
# AUTO-UPDATE CONFIGURATION
# ============================================================================

# Default update intervals (in minutes)
UPDATE_INTERVAL_15M = 5
UPDATE_INTERVAL_1H = 30
UPDATE_INTERVAL_4H = 120
UPDATE_INTERVAL_1D = 360

# Update interval mapping
UPDATE_INTERVALS = {
    '15m': UPDATE_INTERVAL_15M,
    '1h': UPDATE_INTERVAL_1H,
    '4h': UPDATE_INTERVAL_4H,
    '1d': UPDATE_INTERVAL_1D
}


# ============================================================================
# API RATE LIMITING
# ============================================================================

# Binance API rate limit (requests per minute)
BINANCE_RATE_LIMIT = 1200

# Delay between requests during batch operations (seconds)
REQUEST_DELAY_SECONDS = 1.0

# Delay for incremental updates (seconds)
UPDATE_DELAY_SECONDS = 0.5

# Maximum number of requests per timeframe (safety limit)
MAX_REQUESTS_PER_TIMEFRAME = 100


# ============================================================================
# HISTORICAL DATA CONFIGURATION
# ============================================================================

# Number of years of historical data to fetch on initial load
INITIAL_HISTORY_YEARS = 5

# Maximum candles per API request
MAX_CANDLES_PER_REQUEST = 1000


# ============================================================================
# CHART CONFIGURATION
# ============================================================================

# Default number of candles to display in chart
DEFAULT_CHART_CANDLES = 500

# Maximum candles for chart display
MAX_CHART_CANDLES = 10000


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================

# Default lookback period for performance analysis (days)
DEFAULT_PERFORMANCE_DAYS = 90

# FIFO (First In First Out) method for P&L calculation
PNL_CALCULATION_METHOD = 'FIFO'


# ============================================================================
# CANDLESTICK PATTERN DETECTION
# ============================================================================

# Minimum candles needed for pattern detection
MIN_CANDLES_FOR_PATTERNS = 2

# Engulfing pattern detection sensitivity
ENGULFING_TOLERANCE = 0.0001  # Slight tolerance for floating point comparison


# ============================================================================
# TREND ANALYSIS
# ============================================================================

# Default window size for swing point detection
DEFAULT_SWING_WINDOW = 5

# Minimum candles needed for trend analysis
MIN_CANDLES_FOR_TREND = 10


# ============================================================================
# ERROR MESSAGES
# ============================================================================

ERROR_INVALID_TIMEFRAME = 'Invalid timeframe: {timeframe}'
ERROR_INVALID_INDICATOR = 'Invalid indicator: {indicator}'
ERROR_INVALID_LIMIT = 'Limit must be a positive integer between 1 and {max_limit}'
ERROR_INVALID_DAYS = 'Days must be between {min_days} and {max_days}'
ERROR_NO_API_KEYS = 'Binance API keys not configured'
ERROR_NO_DATA = 'No data available for this timeframe'
ERROR_DATABASE_ERROR = 'Database error: {error}'
ERROR_API_ERROR = 'API error: {error}'


# ============================================================================
# SUCCESS MESSAGES
# ============================================================================

SUCCESS_DATA_UPDATED = 'Data updated successfully'
SUCCESS_SYNC_COMPLETE = 'Synchronization completed successfully'
SUCCESS_QUERY_COMPLETE = 'Query completed successfully'
