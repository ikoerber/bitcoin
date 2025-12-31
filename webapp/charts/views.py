"""
Django Views for Bitcoin Trading Dashboard

Provides:
- Frontend dashboard view (HTML template)
- REST API endpoints for OHLCV data, indicators, and price information
"""

import re
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.db.models import Max, Min, Count
import pandas as pd

logger = logging.getLogger(__name__)

from .models import get_model_for_timeframe, TIMEFRAME_MODELS
from .serializers import (
    OHLCVSerializer,
    IndicatorSerializer,
    BollingerBandsSerializer,
    LatestPriceSerializer
)
from .indicators import TechnicalIndicators
from .trading_performance import TradingPerformanceAnalyzer

# Security: Maximum limit for data queries to prevent DoS
MAX_QUERY_LIMIT = 10000
DEFAULT_LIMIT = 500


# ==================== FRONTEND VIEW ====================

def dashboard(request):
    """
    Main dashboard view - renders the HTML template.

    Context includes available timeframes and indicators for the frontend.
    """
    context = {
        'timeframes': ['15m', '1h', '4h', '1d'],
        'indicators': ['RSI', 'SMA', 'EMA', 'Bollinger Bands']
    }
    return render(request, 'charts/dashboard.html', context)


# ==================== REST API VIEWS ====================

class OHLCVDataView(APIView):
    """
    GET /api/ohlcv/<timeframe>/?limit=500&start=&end=

    Returns OHLCV candlestick data for specified timeframe.

    Query Parameters:
        limit (int): Maximum number of candles (default: 500)
        start (str): Start date in YYYY-MM-DD format (optional)
        end (str): End date in YYYY-MM-DD format (optional)

    Returns:
        JSON with timeframe, count, and data array of OHLCV candles
    """

    def get(self, request, timeframe):
        try:
            # Validate timeframe
            model = get_model_for_timeframe(timeframe)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Query parameters with validation
        try:
            limit = int(request.GET.get('limit', DEFAULT_LIMIT))
            if limit <= 0:
                return Response(
                    {'error': 'Limit must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Enforce maximum limit for security
            limit = min(limit, MAX_QUERY_LIMIT)
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_date = request.GET.get('start')  # YYYY-MM-DD format
        end_date = request.GET.get('end')      # YYYY-MM-DD format

        # Validate date formats (YYYY-MM-DD)
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        if start_date and not date_pattern.match(start_date):
            return Response(
                {'error': 'Invalid start_date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if end_date and not date_pattern.match(end_date):
            return Response(
                {'error': 'Invalid end_date format. Use YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Build query
        queryset = model.objects.all()

        if start_date:
            queryset = queryset.filter(datum__gte=start_date)
        if end_date:
            queryset = queryset.filter(datum__lte=end_date)

        # Order by timestamp DESCENDING to get latest data, then limit
        queryset = queryset.order_by('-timestamp')[:limit]

        # Convert to list and reverse to get chronological order for chart
        data_list = list(queryset)
        data_list.reverse()

        # Serialize
        serializer = OHLCVSerializer(data_list, many=True)

        return Response({
            'timeframe': timeframe,
            'count': len(serializer.data),
            'data': serializer.data
        })


class LatestPriceView(APIView):
    """
    GET /api/latest-price/<timeframe>/

    Returns the most recent closing price for a timeframe.

    Returns:
        JSON with timeframe, timestamp, datum, close price, and change percentage
    """

    def get(self, request, timeframe):
        try:
            model = get_model_for_timeframe(timeframe)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Get latest candle
        latest = model.objects.order_by('-timestamp').first()

        if not latest:
            return Response(
                {'error': 'No data available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get previous candle for change calculation (safe index access)
        queryset = model.objects.order_by('-timestamp')[:2]
        candles = list(queryset)

        change_percent = None
        if len(candles) >= 2:
            previous = candles[1]
            try:
                # Prevent division by zero
                if previous.close != 0:
                    change_percent = ((latest.close - previous.close) / previous.close) * 100
            except (ZeroDivisionError, AttributeError) as e:
                logger.warning(f"Could not calculate price change percentage: {e}")
                change_percent = None

        data = {
            'timeframe': timeframe,
            'timestamp': latest.timestamp // 1000,
            'datum': latest.datum,
            'close': latest.close,
            'change_percent': change_percent
        }

        serializer = LatestPriceSerializer(data)
        return Response(serializer.data)


class IndicatorsView(APIView):
    """
    GET /api/indicators/<timeframe>/?indicator=rsi&period=14&limit=500

    Returns calculated technical indicator data.

    Query Parameters:
        indicator (str): Indicator type ('rsi', 'sma', 'ema', 'bb')
        period (int): Indicator period (default: 14 for RSI, 20 for others)
        limit (int): Maximum number of data points (default: 500)

    Supported indicators:
        - rsi: Relative Strength Index
        - sma: Simple Moving Average
        - ema: Exponential Moving Average
        - bb: Bollinger Bands

    Returns:
        JSON with timeframe, indicator type, period, count, and data array
    """

    def get(self, request, timeframe):
        try:
            model = get_model_for_timeframe(timeframe)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Query parameters with validation
        indicator_type = request.GET.get('indicator', 'rsi').lower()

        # Validate indicator type
        valid_indicators = ['rsi', 'sma', 'ema', 'bb']
        if indicator_type not in valid_indicators:
            return Response(
                {'error': f'Invalid indicator. Must be one of: {", ".join(valid_indicators)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate period
        try:
            period = int(request.GET.get('period', 14 if indicator_type == 'rsi' else 20))
            if period <= 0 or period > 200:
                return Response(
                    {'error': 'Period must be between 1 and 200'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid period parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate limit
        try:
            limit = int(request.GET.get('limit', DEFAULT_LIMIT))
            if limit <= 0:
                return Response(
                    {'error': 'Limit must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Enforce maximum limit for security
            limit = min(limit, MAX_QUERY_LIMIT)
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch OHLCV data - get latest data by ordering descending
        queryset = model.objects.order_by('-timestamp')[:limit]

        if not queryset.exists():
            return Response(
                {'error': 'No data available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert to list and reverse to get chronological order
        data = list(queryset.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
        data.reverse()
        df = pd.DataFrame(data)

        # Validate DataFrame has sufficient data for indicator calculation
        if df.empty:
            return Response(
                {'error': 'No data available for indicator calculation'},
                status=status.HTTP_404_NOT_FOUND
            )

        if len(df) < period:
            return Response(
                {
                    'error': f'Insufficient data. Need at least {period} candles for this indicator.',
                    'available': len(df),
                    'required': period
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate indicator
        calc = TechnicalIndicators()

        try:
            if indicator_type == 'rsi':
                values = calc.calculate_rsi(df, period=period)
                result = calc.prepare_indicator_data(df['timestamp'], values)

            elif indicator_type == 'sma':
                values = calc.calculate_sma(df, period=period)
                result = calc.prepare_indicator_data(df['timestamp'], values)

            elif indicator_type == 'ema':
                values = calc.calculate_ema(df, period=period)
                result = calc.prepare_indicator_data(df['timestamp'], values)

            elif indicator_type == 'bb':
                bands = calc.calculate_bollinger_bands(df, period=period)
                result = calc.prepare_bollinger_data(df['timestamp'], bands)

        except Exception as e:
            return Response(
                {'error': f'Error calculating indicator: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            'timeframe': timeframe,
            'indicator': indicator_type,
            'period': period,
            'count': len(result),
            'data': result
        })


class EngulfingPatternsView(APIView):
    """
    GET /api/engulfing/<timeframe>/?limit=500

    Detect and return Bullish/Bearish Engulfing candlestick patterns.

    Parameters:
        - timeframe: 15m, 1h, 4h, 1d
        - limit: Number of candles to analyze (default: 500, max: 10000)

    Returns:
        JSON with list of detected engulfing patterns including type, price, and strength
    """

    def get(self, request, timeframe):
        # Validate timeframe
        if timeframe not in TIMEFRAME_MODELS:
            return Response(
                {'error': f'Invalid timeframe: {timeframe}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get parameters
        try:
            limit = int(request.GET.get('limit', 500))
            if limit <= 0:
                return Response(
                    {'error': 'Limit must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            limit = min(limit, 10000)
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch OHLCV data
        model = TIMEFRAME_MODELS[timeframe]
        queryset = model.objects.order_by('-timestamp')[:limit]

        if not queryset.exists():
            return Response(
                {'error': 'No data available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert to DataFrame
        data = list(queryset.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
        data.reverse()  # Chronological order
        df = pd.DataFrame(data)

        # Detect engulfing patterns
        calc = TechnicalIndicators()

        try:
            patterns = calc.detect_engulfing_patterns(df)

            return Response({
                'timeframe': timeframe,
                'count': len(patterns),
                'patterns': patterns
            })

        except Exception as e:
            logger.error(f"Error detecting engulfing patterns: {e}")
            return Response(
                {'error': f'Error detecting engulfing patterns: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DataSummaryView(APIView):
    """
    GET /api/summary/

    Returns summary statistics for all timeframes.

    Returns:
        JSON with database summary for each timeframe (count, earliest, latest dates)
    """

    def get(self, request):
        summary = {}

        for timeframe, model in TIMEFRAME_MODELS.items():
            stats = model.objects.aggregate(
                count=Count('timestamp'),
                earliest=Min('datum'),
                latest=Max('datum')
            )

            summary[timeframe] = {
                'table': model._meta.db_table,
                'records': stats['count'],
                'earliest': stats['earliest'],
                'latest': stats['latest']
            }

        return Response(summary)


class UpdateDatabaseView(APIView):
    """
    POST /api/update-database/

    Triggers database update by running db_manager.py script.

    Returns:
        JSON with update status and results
    """

    def post(self, request):
        import subprocess
        import sys
        from pathlib import Path
        from django.conf import settings

        try:
            # Path to db_manager.py (one level up from webapp directory)
            db_manager_path = settings.BASE_DIR.parent / 'db_manager.py'

            # Security checks for subprocess execution
            if not db_manager_path.exists():
                return Response(
                    {'error': f'db_manager.py not found at {db_manager_path}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            if not db_manager_path.is_file():
                return Response(
                    {'error': 'db_manager.py is not a regular file'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Verify file permissions (should not be world-writable on Unix systems)
            import os
            stat_info = db_manager_path.stat()
            if hasattr(stat_info, 'st_mode') and (stat_info.st_mode & 0o002):
                logger.warning(f'db_manager.py has insecure permissions (world-writable): {oct(stat_info.st_mode)}')

            # Run db_manager.py as subprocess with security measures
            result = subprocess.run(
                [sys.executable, str(db_manager_path.resolve())],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
                cwd=str(db_manager_path.parent),  # Set working directory explicitly
                env=os.environ.copy()  # Use clean environment copy
            )

            # Parse output
            success = result.returncode == 0

            return Response({
                'success': success,
                'message': 'Database update completed' if success else 'Database update failed',
                'stdout': result.stdout[-1000:] if result.stdout else '',  # Last 1000 chars
                'stderr': result.stderr[-1000:] if result.stderr else '',
                'return_code': result.returncode
            })

        except subprocess.TimeoutExpired:
            return Response(
                {'error': 'Database update timed out (exceeded 5 minutes)'},
                status=status.HTTP_408_REQUEST_TIMEOUT
            )
        except Exception as e:
            return Response(
                {'error': f'Error running database update: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TrendView(APIView):
    """
    GET /api/trend/<timeframe>/?lookback=5&min_move=0.5&limit=500

    Detect trend direction using Higher Highs/Higher Lows methodology.

    Parameters:
        - timeframe: 15m, 1h, 4h, 1d
        - lookback: Swing point detection window (default: 5, range: 3-20)
        - min_move: Minimum % move between swings (default: 0.5%)
        - limit: Number of candles to analyze (default: 500, max: 10000)

    Returns:
        JSON with trend_type, trendline coordinates, swing points, and statistics
    """

    def get(self, request, timeframe):
        # Validate timeframe
        if timeframe not in TIMEFRAME_MODELS:
            return Response(
                {'error': f'Invalid timeframe: {timeframe}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate lookback parameter
        try:
            lookback = int(request.GET.get('lookback', 5))
            if lookback < 3 or lookback > 20:
                return Response(
                    {'error': 'lookback must be between 3 and 20'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid lookback parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate min_move parameter
        try:
            min_move = float(request.GET.get('min_move', 0.5))
            if min_move < 0 or min_move > 10:
                return Response(
                    {'error': 'min_move must be between 0 and 10'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid min_move parameter. Must be a number.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate limit parameter
        try:
            limit = int(request.GET.get('limit', 500))
            if limit <= 0:
                return Response(
                    {'error': 'Limit must be a positive integer'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            limit = min(limit, MAX_QUERY_LIMIT)
        except ValueError:
            return Response(
                {'error': 'Invalid limit parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch OHLCV data
        model = TIMEFRAME_MODELS[timeframe]
        queryset = model.objects.order_by('-timestamp')[:limit]

        if not queryset.exists():
            return Response(
                {'error': 'No data available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert to DataFrame
        data = list(queryset.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
        data.reverse()  # Chronological order
        df = pd.DataFrame(data)

        # Validate sufficient data
        min_required = 2 * lookback + 3
        if len(df) < min_required:
            return Response(
                {
                    'error': f'Insufficient data. Need at least {min_required} candles.',
                    'available': len(df),
                    'required': min_required
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Detect trend
        calc = TechnicalIndicators()

        try:
            trend_data = calc.detect_trend(df, lookback=lookback, min_move_percent=min_move)

            return Response({
                'timeframe': timeframe,
                'lookback': lookback,
                'min_move_percent': min_move,
                'trend_type': trend_data['trend_type'],
                'confidence': trend_data['confidence'],
                'trendline_points': trend_data['trendline_points'],
                'swing_points': trend_data['swing_points'],
                'statistics': {
                    'swing_highs': trend_data['swing_highs_count'],
                    'swing_lows': trend_data['swing_lows_count'],
                    'higher_highs': trend_data['higher_high_count'],
                    'lower_highs': trend_data['lower_high_count'],
                    'higher_lows': trend_data['higher_low_count'],
                    'lower_lows': trend_data['lower_low_count']
                }
            })

        except Exception as e:
            logger.error(f"Error detecting trend: {e}")
            return Response(
                {'error': f'Error detecting trend: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TradingPerformanceView(APIView):
    """
    GET /api/trading-performance/?days=90

    Analyze personal trading performance from Binance account.

    Parameters:
        - days: Number of days to look back (default: 90, max: 365)

    Returns:
        JSON with trading performance metrics including:
        - Total trades, buy/sell counts
        - Volume in BTC and EUR
        - Fees in BNB and EUR (converted)
        - Realized P&L
        - Win-rate and ROI
        - Account balances

    Requires:
        - BINANCE_API_KEY and BINANCE_API_SECRET in environment variables
        - Read-only API permissions
    """

    def get(self, request):
        from django.conf import settings
        from datetime import datetime, timedelta

        # Check if API keys are configured
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
            return Response(
                {
                    'error': 'Binance API keys not configured',
                    'message': 'Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables in .env file'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        # Get parameters
        try:
            days = int(request.GET.get('days', 90))
            if days <= 0 or days > 365:
                return Response(
                    {'error': 'days must be between 1 and 365'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {'error': 'Invalid days parameter. Must be an integer.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Calculate date range
            since = datetime.now() - timedelta(days=days)

            # Fetch trade history
            logger.info(f"Fetching trade history for last {days} days")
            trades = analyzer.fetch_trade_history(
                symbol='BTC/EUR',
                since=since,
                limit=1000
            )

            if not trades:
                return Response({
                    'days': days,
                    'total_trades': 0,
                    'message': 'No trades found in the specified period'
                })

            # Get current BNB/EUR price
            bnb_eur_price = analyzer.get_current_bnb_eur_price()

            # Calculate performance metrics
            logger.info(f"Calculating performance metrics for {len(trades)} trades")
            metrics = analyzer.calculate_performance_metrics(trades, bnb_eur_price)

            # Get account balance
            try:
                balance = analyzer.get_account_balance()
            except Exception as e:
                logger.warning(f"Could not fetch account balance: {e}")
                balance = None

            # Prepare response
            return Response({
                'period': {
                    'days': days,
                    'from': since.isoformat(),
                    'to': datetime.now().isoformat()
                },
                'metrics': metrics,
                'balance': balance,
                'timestamp': datetime.now().isoformat()
            })

        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            return Response(
                {
                    'error': 'Configuration error',
                    'message': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error analyzing trading performance: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error analyzing trading performance',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
