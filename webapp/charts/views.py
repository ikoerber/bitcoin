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


def cashflow(request):
    """
    Cashflow timeline view - renders the cashflow template.

    Shows all transactions (deposits, trades, converts, open orders) in chronological order.
    """
    return render(request, 'charts/cashflow.html')


def balance_history(request):
    """
    Balance history view - renders the balance history template.

    Shows daily balance evolution for EUR, BTC, BNB with total portfolio value in EUR.
    """
    return render(request, 'charts/balance-history.html')


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
    GET /api/trading-performance/?days=90&groupby=day

    Analyze personal trading performance from Binance account.

    Parameters:
        - days: Number of days to look back (default: 90, max: 365)
        - groupby: Optional grouping ('day' for daily breakdown)

    Returns (without groupby):
        JSON with overall trading performance metrics:
        - Total trades, buy/sell counts
        - Volume in BTC and EUR
        - Fees in BNB and EUR (converted)
        - Realized P&L
        - Win-rate and ROI
        - Account balances

    Returns (with groupby=day):
        JSON with daily breakdown:
        - Array of daily metrics (date, trades, volume, fees, P&L)
        - Each day's realized P&L calculated using FIFO

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

        # Get groupby parameter
        groupby = request.GET.get('groupby', None)
        if groupby and groupby not in ['day']:
            return Response(
                {'error': 'groupby must be "day" (other options coming soon)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Calculate date range
            since = datetime.now() - timedelta(days=days)

            # Load trade history from local database (fast, no API limits)
            logger.info(f"Loading trade history from database for last {days} days")
            trades = analyzer.get_trades_from_database(
                symbol='BTC/EUR',
                since=since
            )

            if not trades:
                return Response({
                    'days': days,
                    'total_trades': 0,
                    'message': 'No trades found in the specified period'
                })

            # Get current BNB/EUR price
            bnb_eur_price = analyzer.get_current_bnb_eur_price()

            # Check if daily grouping is requested
            if groupby == 'day':
                # Calculate daily performance
                logger.info(f"Calculating daily performance metrics for {len(trades)} trades")
                daily_metrics = analyzer.calculate_daily_performance(trades, bnb_eur_price)

                return Response({
                    'period': {
                        'days': days,
                        'from': since.isoformat(),
                        'to': datetime.now().isoformat(),
                        'groupby': 'day'
                    },
                    'daily_data': daily_metrics,
                    'total_days': len(daily_metrics),
                    'timestamp': datetime.now().isoformat()
                })

            # Calculate overall performance metrics
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


class SyncTradesView(APIView):
    """
    API endpoint to synchronize trades from Binance to local database.

    GET /api/sync-trades/
        Triggers incremental sync of BTC/EUR trades from Binance API to SQLite database.
        Only fetches new trades since last sync (efficient).

    Query parameters:
        - symbol: Trading pair (default: BTC/EUR)
        - full_sync: Set to 'true' to force full resync from 1 year ago (default: false)

    Returns:
        JSON with sync statistics:
        - trades_synced: Number of new trades added
        - total_trades_in_db: Total trades in database
        - latest_trade_datetime: Most recent trade timestamp

    Requires:
        - BINANCE_API_KEY and BINANCE_API_SECRET in environment variables
        - Read-only API permissions
    """

    def get(self, request):
        from django.conf import settings

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
        symbol = request.GET.get('symbol', 'BTC/EUR')
        full_sync = request.GET.get('full_sync', 'false').lower() == 'true'

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Determine sync start date
            since = None
            if full_sync:
                # Force full sync from 1 year ago
                from datetime import datetime, timedelta
                since = datetime.now() - timedelta(days=365)
                logger.info(f"Full sync requested: fetching all trades since {since}")

            # Sync trades to database
            logger.info(f"Starting trade synchronization for {symbol}")
            sync_result = analyzer.sync_trades_to_database(
                symbol=symbol,
                since=since
            )

            logger.info(f"Trade sync complete: {sync_result}")

            return Response({
                'status': 'success',
                'sync_type': 'full' if full_sync else 'incremental',
                **sync_result
            })

        except ValueError as e:
            return Response(
                {
                    'error': 'Configuration error',
                    'message': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error syncing trades: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error syncing trades',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncAssetHistoryView(APIView):
    """
    API endpoint to synchronize asset history (deposits, withdrawals, converts).

    GET /api/sync-asset-history/
        Syncs deposits, withdrawals, and converts from Binance API to database.
        Only fetches successful transactions.

    Query parameters:
        - full_sync: Set to 'true' to force full resync from 1 year ago (default: false)

    Returns:
        JSON with sync statistics:
        - deposits_synced: Number of new deposits added
        - withdrawals_synced: Number of new withdrawals added
        - converts_synced: Number of new converts added
        - total_in_db: Total counts by transaction type

    Requires:
        - BINANCE_API_KEY and BINANCE_API_SECRET in environment variables
        - Read-only API permissions
    """

    def get(self, request):
        from django.conf import settings

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
        full_sync = request.GET.get('full_sync', 'false').lower() == 'true'

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Determine sync start date
            since = None
            if full_sync:
                from datetime import datetime, timedelta
                since = datetime.now() - timedelta(days=365)
                logger.info(f"Full asset history sync requested: fetching since {since}")

            # Sync asset history to database
            logger.info("Starting asset history synchronization")
            sync_result = analyzer.sync_asset_history_to_database(since=since)

            logger.info(f"Asset history sync complete: {sync_result}")

            return Response({
                'status': 'success',
                'sync_type': 'full' if full_sync else 'incremental',
                **sync_result
            })

        except ValueError as e:
            return Response(
                {
                    'error': 'Configuration error',
                    'message': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error syncing asset history: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error syncing asset history',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SyncOpenOrdersView(APIView):
    """
    API endpoint to synchronize currently open orders from Binance.

    GET /api/sync-open-orders/
        Fetches all currently open limit orders and stores them in database.
        Replaces previous data to always show current state.

    Query parameters:
        - symbol: Trading pair (default: BTC/EUR)

    Returns:
        JSON with open orders statistics:
        - total_open_orders: Total number of open orders
        - buy_orders: Number of buy orders
        - sell_orders: Number of sell orders
        - buy_amount_btc: Total BTC in buy orders
        - sell_amount_btc: Total BTC in sell orders

    Requires:
        - BINANCE_API_KEY and BINANCE_API_SECRET in environment variables
        - Read-only API permissions
    """

    def get(self, request):
        from django.conf import settings

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
        symbol = request.GET.get('symbol', 'BTC/EUR')

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Sync open orders
            logger.info(f"Syncing open orders for {symbol}")
            sync_result = analyzer.sync_open_orders_to_database(symbol=symbol)

            logger.info(f"Open orders sync complete: {sync_result}")

            return Response(sync_result)

        except ValueError as e:
            return Response(
                {
                    'error': 'Configuration error',
                    'message': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error syncing open orders: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error syncing open orders',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccountBalanceView(APIView):
    """
    API endpoint to get current account balances for BTC, EUR, and BNB.

    GET /api/account-balance/
        Fetches current balances from Binance account.

    Returns:
        JSON with account balances:
        {
            'BTC': {'free': 0.05, 'locked': 0.01, 'total': 0.06},
            'EUR': {'free': 1000.0, 'locked': 0.0, 'total': 1000.0},
            'BNB': {'free': 0.5, 'locked': 0.0, 'total': 0.5},
            'timestamp': 1640000000000,
            'datetime': '2025-12-31 12:00:00'
        }

    Requires:
        - BINANCE_API_KEY and BINANCE_API_SECRET in environment variables
        - Read-only API permissions
    """

    def get(self, request):
        from django.conf import settings

        # Check if API keys are configured
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
            return Response(
                {
                    'error': 'Binance API keys not configured',
                    'message': 'Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables in .env file'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Get account balances
            logger.info("Fetching account balances")
            balances = analyzer.get_account_balances()

            logger.info(f"Account balances retrieved: {balances}")

            return Response(balances)

        except ValueError as e:
            return Response(
                {
                    'error': 'Configuration error',
                    'message': str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logger.error(f"Error fetching account balances: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error fetching account balances',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CashflowView(APIView):
    """
    API endpoint to get all cashflow transactions (deposits, trades, converts, orders).

    GET /api/cashflow/
        Returns all transactions from all sources in chronological order.

    Query parameters:
        - limit: Max number of transactions to return (default: 100)
        - days: Number of days to look back (default: 30)
        - type: Filter by type (deposit, withdrawal, trade, convert, order)

    Returns:
        JSON array of transactions with individual cashflows
    """

    def get(self, request):
        import sqlite3
        from django.conf import settings

        # Get query parameters
        limit = int(request.GET.get('limit', 100))
        days = int(request.GET.get('days', 30))
        type_filter = request.GET.get('type', None)

        # Validate limits
        if limit > 1000:
            limit = 1000
        if days > 365:
            days = 365

        # Calculate timestamp threshold
        from datetime import datetime, timedelta
        threshold_date = datetime.now() - timedelta(days=days)
        threshold_timestamp = int(threshold_date.timestamp() * 1000)

        try:
            # Connect to database
            db_path = settings.DATABASES['default']['NAME']

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                transactions = []

                # 1. Get asset transactions (deposits, withdrawals, converts, transfers)
                cursor.execute("""
                    SELECT
                        transaction_id as id,
                        timestamp,
                        datetime,
                        transaction_type as type,
                        status,
                        currency,
                        amount,
                        from_currency,
                        to_currency,
                        from_amount,
                        fee,
                        fee_currency,
                        network,
                        address
                    FROM asset_transactions
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (threshold_timestamp,))

                for row in cursor.fetchall():
                    tx_type = row['type']
                    description = ''

                    if tx_type == 'deposit':
                        description = f"{row['currency']} Deposit"
                        if row['network']:
                            description += f" via {row['network']}"
                    elif tx_type == 'withdrawal':
                        description = f"{row['currency']} Withdrawal"
                        if row['network']:
                            description += f" via {row['network']}"
                    elif tx_type == 'convert':
                        description = f"Convert {row['from_amount']} {row['from_currency']} → {row['amount']} {row['to_currency']}"
                    elif tx_type == 'transfer':
                        description = f"{row['currency']} Internal Transfer"

                    transactions.append({
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'datetime': row['datetime'],
                        'type': tx_type,
                        'status': row['status'] or 'completed',
                        'currency': row['currency'],
                        'amount': float(row['amount']) if row['amount'] else 0.0,
                        'price': None,
                        'from_currency': row['from_currency'],
                        'to_currency': row['to_currency'],
                        'from_amount': float(row['from_amount']) if row['from_amount'] else None,
                        'to_amount': float(row['amount']) if row['amount'] and tx_type == 'convert' else None,
                        'fee': float(row['fee']) if row['fee'] else 0.0,
                        'fee_currency': row['fee_currency'],
                        'description': description
                    })

                # 2. Get trades (buy/sell orders)
                cursor.execute("""
                    SELECT
                        trade_id as id,
                        timestamp,
                        datetime,
                        side,
                        price,
                        amount,
                        cost,
                        fee_cost,
                        fee_currency,
                        is_maker
                    FROM btc_eur_trades
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (threshold_timestamp,))

                for row in cursor.fetchall():
                    side = row['side']
                    amount_btc = float(row['amount'])
                    cost_eur = float(row['cost'])
                    price = float(row['price'])

                    if side == 'buy':
                        description = f"Buy {amount_btc:.8f} BTC @ €{price:.2f}"
                        currency = 'EUR'
                        amount = -cost_eur  # Negative = money out
                    else:  # sell
                        description = f"Sell {amount_btc:.8f} BTC @ €{price:.2f}"
                        currency = 'EUR'
                        amount = cost_eur  # Positive = money in

                    transactions.append({
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'datetime': row['datetime'],
                        'type': side,
                        'status': 'completed',
                        'currency': currency,
                        'amount': amount,
                        'amount_btc': amount_btc,
                        'price': price,
                        'from_currency': None,
                        'to_currency': None,
                        'from_amount': None,
                        'to_amount': None,
                        'fee': float(row['fee_cost']) if row['fee_cost'] else 0.0,
                        'fee_currency': row['fee_currency'],
                        'is_maker': bool(row['is_maker']),
                        'description': description
                    })

                # 3. Get open orders (pending cashflow)
                cursor.execute("""
                    SELECT
                        order_id as id,
                        timestamp,
                        datetime,
                        side,
                        price,
                        amount,
                        remaining,
                        status
                    FROM open_orders
                    WHERE symbol = 'BTC/EUR'
                    ORDER BY timestamp DESC
                """)

                for row in cursor.fetchall():
                    side = row['side']
                    remaining_btc = float(row['remaining'])
                    price = float(row['price'])
                    cost_eur = remaining_btc * price

                    if side == 'buy':
                        description = f"Open Limit Buy {remaining_btc:.8f} BTC @ €{price:.2f}"
                        currency = 'EUR'
                        amount = -cost_eur  # Will be spent when filled
                    else:  # sell
                        description = f"Open Limit Sell {remaining_btc:.8f} BTC @ €{price:.2f}"
                        currency = 'EUR'
                        amount = cost_eur  # Will be received when filled

                    transactions.append({
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'datetime': row['datetime'],
                        'type': f'limit_{side}',
                        'status': 'open',
                        'currency': currency,
                        'amount': amount,
                        'amount_btc': remaining_btc,
                        'price': price,
                        'from_currency': None,
                        'to_currency': None,
                        'from_amount': None,
                        'to_amount': None,
                        'fee': 0.0,
                        'fee_currency': None,
                        'description': description
                    })

                # Sort all transactions by timestamp (newest first)
                transactions.sort(key=lambda x: x['timestamp'], reverse=True)

                # Apply type filter if specified
                if type_filter:
                    transactions = [tx for tx in transactions if tx['type'] == type_filter]

                # Apply limit
                transactions = transactions[:limit]

                logger.info(f"Cashflow query: {len(transactions)} transactions (last {days} days)")

                return Response({
                    'transactions': transactions,
                    'total_count': len(transactions),
                    'days': days,
                    'limit': limit
                })

        except Exception as e:
            logger.error(f"Error fetching cashflow: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error fetching cashflow',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BalanceHistoryView(APIView):
    """
    API endpoint to get daily balance history with EUR conversion.

    GET /api/balance-history/
        Returns daily snapshots of EUR, BTC, BNB balances with total in EUR.

    Query parameters:
        - days: Number of days to look back (default: 30, max: 365)

    Returns:
        JSON with daily balance data:
        {
            'dates': ['2025-12-01', '2025-12-02', ...],
            'eur_balance': [1000.0, 950.0, ...],
            'btc_balance': [0.01, 0.015, ...],
            'bnb_balance': [0.5, 0.48, ...],
            'btc_value_eur': [750.0, 1125.0, ...],
            'bnb_value_eur': [350.0, 336.0, ...],
            'total_value_eur': [2100.0, 2411.0, ...],
            'current_prices': {
                'btc_eur': 75000.0,
                'bnb_eur': 700.0
            }
        }
    """

    def get(self, request):
        import sqlite3
        from django.conf import settings
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Get query parameters
        days = int(request.GET.get('days', 30))
        if days > 365:
            days = 365

        try:
            # Get current BTC/EUR and BNB/EUR prices
            from .trading_performance import TradingPerformanceAnalyzer
            analyzer = TradingPerformanceAnalyzer()

            btc_eur_price = analyzer.exchange.fetch_ticker('BTC/EUR')['last']
            bnb_eur_price = analyzer.exchange.fetch_ticker('BNB/EUR')['last']

            logger.info(f"Current prices: BTC/EUR={btc_eur_price:.2f}, BNB/EUR={bnb_eur_price:.2f}")

            # Connect to database
            db_path = settings.DATABASES['default']['NAME']

            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Calculate date range
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)

                # Initialize daily balance tracking
                daily_deltas = defaultdict(lambda: {'eur': 0, 'btc': 0, 'bnb': 0})

                # 1. Get asset transactions (deposits, withdrawals)
                cursor.execute("""
                    SELECT
                        date(datetime) as date,
                        currency,
                        SUM(CASE WHEN transaction_type IN ('deposit', 'transfer') THEN amount ELSE -amount END) as net_amount
                    FROM asset_transactions
                    WHERE date(datetime) >= ?
                    GROUP BY date(datetime), currency
                """, (start_date.isoformat(),))

                for row in cursor.fetchall():
                    date = row['date']
                    currency = row['currency'].upper()
                    amount = float(row['net_amount'])

                    if currency == 'EUR':
                        daily_deltas[date]['eur'] += amount
                    elif currency == 'BTC':
                        daily_deltas[date]['btc'] += amount
                    elif currency == 'BNB':
                        daily_deltas[date]['bnb'] += amount

                # 2. Get trades (BTC buys/sells affect EUR and BTC)
                cursor.execute("""
                    SELECT
                        date(datetime) as date,
                        SUM(CASE WHEN side = 'buy' THEN amount ELSE -amount END) as btc_delta,
                        SUM(CASE WHEN side = 'buy' THEN -cost ELSE cost END) as eur_delta,
                        SUM(CASE WHEN fee_currency = 'BNB' THEN -fee_cost ELSE 0 END) as bnb_fees
                    FROM btc_eur_trades
                    WHERE date(datetime) >= ?
                    GROUP BY date(datetime)
                """, (start_date.isoformat(),))

                for row in cursor.fetchall():
                    date = row['date']
                    daily_deltas[date]['btc'] += float(row['btc_delta'] or 0)
                    daily_deltas[date]['eur'] += float(row['eur_delta'] or 0)
                    daily_deltas[date]['bnb'] += float(row['bnb_fees'] or 0)

                # 3. Build cumulative daily balances
                dates = []
                eur_balance = []
                btc_balance = []
                bnb_balance = []
                btc_value_eur = []
                bnb_value_eur = []
                total_value_eur = []

                # Start with initial balances (0 or fetch from earliest known state)
                cumulative_eur = 0
                cumulative_btc = 0
                cumulative_bnb = 0

                # Generate daily data points
                current_date = start_date
                while current_date <= end_date:
                    date_str = current_date.isoformat()

                    # Apply deltas for this day
                    if date_str in daily_deltas:
                        cumulative_eur += daily_deltas[date_str]['eur']
                        cumulative_btc += daily_deltas[date_str]['btc']
                        cumulative_bnb += daily_deltas[date_str]['bnb']

                    # Calculate EUR values
                    btc_eur_value = cumulative_btc * btc_eur_price
                    bnb_eur_value = cumulative_bnb * bnb_eur_price
                    total_eur = cumulative_eur + btc_eur_value + bnb_eur_value

                    # Store data points
                    dates.append(date_str)
                    eur_balance.append(round(cumulative_eur, 2))
                    btc_balance.append(round(cumulative_btc, 8))
                    bnb_balance.append(round(cumulative_bnb, 8))
                    btc_value_eur.append(round(btc_eur_value, 2))
                    bnb_value_eur.append(round(bnb_eur_value, 2))
                    total_value_eur.append(round(total_eur, 2))

                    current_date += timedelta(days=1)

                logger.info(f"Balance history: {len(dates)} days, total EUR: {total_value_eur[-1] if total_value_eur else 0:.2f}")

                # 4. Calculate flow data for Sankey diagram
                flows = {
                    'deposits_to_eur': 0,
                    'eur_to_btc': 0,
                    'btc_to_eur': 0,
                    'eur_to_bnb': 0,
                    'bnb_to_fees': 0,
                    'eur_to_withdrawals': 0
                }

                # Deposits
                cursor.execute("""
                    SELECT SUM(amount) as total
                    FROM asset_transactions
                    WHERE transaction_type = 'deposit'
                      AND currency = 'EUR'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                flows['deposits_to_eur'] = round(float(result['total'] or 0), 2)

                # EUR to BTC (buys)
                cursor.execute("""
                    SELECT SUM(cost) as total
                    FROM btc_eur_trades
                    WHERE side = 'buy'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                flows['eur_to_btc'] = round(float(result['total'] or 0), 2)

                # BTC to EUR (sells)
                cursor.execute("""
                    SELECT SUM(cost) as total
                    FROM btc_eur_trades
                    WHERE side = 'sell'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                flows['btc_to_eur'] = round(float(result['total'] or 0), 2)

                # BNB fees (converted to EUR)
                cursor.execute("""
                    SELECT SUM(fee_cost) as total
                    FROM btc_eur_trades
                    WHERE fee_currency = 'BNB'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                bnb_fees_bnb = float(result['total'] or 0)
                flows['bnb_to_fees'] = round(bnb_fees_bnb * bnb_eur_price, 2)

                # Converts EUR to BNB
                cursor.execute("""
                    SELECT SUM(from_amount) as total
                    FROM asset_transactions
                    WHERE transaction_type = 'convert'
                      AND from_currency = 'EUR'
                      AND to_currency = 'BNB'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                flows['eur_to_bnb'] = round(float(result['total'] or 0), 2)

                # Withdrawals
                cursor.execute("""
                    SELECT SUM(amount) as total
                    FROM asset_transactions
                    WHERE transaction_type = 'withdrawal'
                      AND currency = 'EUR'
                      AND date(datetime) >= ?
                """, (start_date.isoformat(),))
                result = cursor.fetchone()
                flows['eur_to_withdrawals'] = round(float(result['total'] or 0), 2)

                return Response({
                    'dates': dates,
                    'eur_balance': eur_balance,
                    'btc_balance': btc_balance,
                    'bnb_balance': bnb_balance,
                    'btc_value_eur': btc_value_eur,
                    'bnb_value_eur': bnb_value_eur,
                    'total_value_eur': total_value_eur,
                    'current_prices': {
                        'btc_eur': round(btc_eur_price, 2),
                        'bnb_eur': round(bnb_eur_price, 2)
                    },
                    'flows': flows,
                    'days': days
                })

        except Exception as e:
            logger.error(f"Error fetching balance history: {e}", exc_info=True)
            return Response(
                {
                    'error': 'Error fetching balance history',
                    'message': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
