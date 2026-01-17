"""
Shared utility functions for the charts application.

Centralizes common validation, formatting, and helper functions
to eliminate code duplication across views and modules.
"""

import os
from datetime import datetime
from functools import wraps
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_positive_integer(value, param_name='value', max_value=None):
    """
    Validate that a value is a positive integer.

    Args:
        value: Value to validate (can be string or int)
        param_name: Name of parameter (for error messages)
        max_value: Optional maximum value to cap at

    Returns:
        int: Validated and optionally capped integer

    Raises:
        ValueError: If value is not a valid positive integer
    """
    try:
        int_value = int(value)
        if int_value <= 0:
            raise ValueError(f'{param_name} must be a positive integer')

        if max_value is not None:
            int_value = min(int_value, max_value)

        return int_value
    except (TypeError, ValueError) as e:
        raise ValueError(f'Invalid {param_name} parameter. Must be a positive integer.')


def validate_timeframe(timeframe, valid_timeframes=None):
    """
    Validate that a timeframe is valid.

    Args:
        timeframe: Timeframe string to validate
        valid_timeframes: List of valid timeframes (defaults to standard ones)

    Returns:
        str: Validated timeframe

    Raises:
        ValueError: If timeframe is invalid
    """
    if valid_timeframes is None:
        valid_timeframes = ['15m', '1h', '4h', '1d']

    if timeframe not in valid_timeframes:
        raise ValueError(f'Invalid timeframe: {timeframe}. Must be one of: {", ".join(valid_timeframes)}')

    return timeframe


def validate_indicator_type(indicator_type):
    """
    Validate that an indicator type is valid.

    Args:
        indicator_type: Indicator type string to validate

    Returns:
        str: Validated indicator type

    Raises:
        ValueError: If indicator type is invalid
    """
    valid_indicators = ['rsi', 'sma', 'ema', 'bb']

    if indicator_type not in valid_indicators:
        raise ValueError(f'Invalid indicator. Must be one of: {", ".join(valid_indicators)}')

    return indicator_type


# ============================================================================
# RESPONSE HELPERS
# ============================================================================

def error_response(message, status_code=status.HTTP_400_BAD_REQUEST, **extra_data):
    """
    Create a standardized error response.

    Args:
        message: Error message
        status_code: HTTP status code
        **extra_data: Additional data to include in response

    Returns:
        Response: DRF Response object with error
    """
    data = {'error': message}
    data.update(extra_data)
    return Response(data, status=status_code)


def success_response(data, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response.

    Args:
        data: Response data (dict)
        status_code: HTTP status code

    Returns:
        Response: DRF Response object
    """
    return Response(data, status=status_code)


# ============================================================================
# DECORATORS
# ============================================================================

def require_binance_api_keys(view_func):
    """
    Decorator to check if Binance API keys are configured.

    Returns 503 error if keys are not set.
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
            return error_response(
                'Binance API keys not configured',
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message='Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables in .env file'
            )
        return view_func(self, request, *args, **kwargs)
    return wrapper


# ============================================================================
# DATA FORMATTING HELPERS
# ============================================================================

def timestamp_to_datetime(timestamp_ms):
    """
    Convert millisecond timestamp to formatted datetime string.

    Args:
        timestamp_ms: Timestamp in milliseconds

    Returns:
        str: Formatted datetime string (YYYY-MM-DD HH:MM:SS)
    """
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')


def safe_float(value, default=0.0):
    """
    Safely convert value to float.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        float: Converted value or default
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    """
    Safely convert value to int.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        int: Converted value or default
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ============================================================================
# DATABASE HELPERS
# ============================================================================

def get_database_path(db_path=None):
    """
    Get the database path, with fallback to default location.

    Args:
        db_path: Optional explicit database path

    Returns:
        str: Absolute path to database file
    """
    if db_path is None:
        # Default: project_root/btc_eur_data.db
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(project_root, 'btc_eur_data.db')

    return db_path


def execute_query_safely(cursor, query, params=None, fetch_one=True):
    """
    Execute SQL query with error handling.

    Args:
        cursor: Database cursor
        query: SQL query string
        params: Query parameters (optional)
        fetch_one: If True, return fetchone(), else fetchall()

    Returns:
        Query result or None if error
    """
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        return cursor.fetchone() if fetch_one else cursor.fetchall()
    except Exception as e:
        print(f"Database query error: {e}")
        return None


# ============================================================================
# REQUEST PARAMETER EXTRACTION
# ============================================================================

def get_limit_param(request, default=500, max_limit=10000):
    """
    Extract and validate 'limit' parameter from request.

    Args:
        request: Django request object
        default: Default limit value
        max_limit: Maximum allowed limit

    Returns:
        tuple: (limit_value, error_response or None)
    """
    try:
        limit = int(request.GET.get('limit', default))
        if limit <= 0:
            return None, error_response('Limit must be a positive integer')
        limit = min(limit, max_limit)
        return limit, None
    except ValueError:
        return None, error_response('Invalid limit parameter. Must be an integer.')


def get_days_param(request, default=90, min_days=1, max_days=365):
    """
    Extract and validate 'days' parameter from request.

    Args:
        request: Django request object
        default: Default days value
        min_days: Minimum allowed days
        max_days: Maximum allowed days

    Returns:
        tuple: (days_value, error_response or None)
    """
    try:
        days = int(request.GET.get('days', default))
        if days < min_days or days > max_days:
            return None, error_response(f'Days must be between {min_days} and {max_days}')
        return days, None
    except ValueError:
        return None, error_response('Invalid days parameter. Must be an integer.')


def get_period_param(request, default=14, min_period=1, max_period=200):
    """
    Extract and validate 'period' parameter from request.

    Args:
        request: Django request object
        default: Default period value
        min_period: Minimum allowed period
        max_period: Maximum allowed period

    Returns:
        tuple: (period_value, error_response or None)
    """
    try:
        period = int(request.GET.get('period', default))
        if period < min_period or period > max_period:
            return None, error_response(f'Period must be between {min_period} and {max_period}')
        return period, None
    except ValueError:
        return None, error_response('Invalid period parameter. Must be an integer.')
