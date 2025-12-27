"""
Django Views for Bitcoin Trading Dashboard

Provides:
- Frontend dashboard view (HTML template)
- REST API endpoints for OHLCV data, indicators, and price information
"""

import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.db.models import Max, Min, Count
import pandas as pd

from .models import get_model_for_timeframe, TIMEFRAME_MODELS
from .serializers import (
    OHLCVSerializer,
    IndicatorSerializer,
    BollingerBandsSerializer,
    LatestPriceSerializer
)
from .indicators import TechnicalIndicators

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

        # Get previous candle for change calculation
        previous = model.objects.order_by('-timestamp')[1:2].first()

        change_percent = None
        if previous:
            change_percent = ((latest.close - previous.close) / previous.close) * 100

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

            if not db_manager_path.exists():
                return Response(
                    {'error': f'db_manager.py not found at {db_manager_path}'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Run db_manager.py as subprocess
            result = subprocess.run(
                [sys.executable, str(db_manager_path)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
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
