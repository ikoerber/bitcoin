"""
Django Views for Bitcoin Trading Dashboard

Provides:
- Frontend dashboard view (HTML template)
- REST API endpoints for OHLCV data, indicators, and price information
"""

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

        # Query parameters
        limit = int(request.GET.get('limit', 500))
        start_date = request.GET.get('start')  # YYYY-MM-DD format
        end_date = request.GET.get('end')      # YYYY-MM-DD format

        # Build query
        queryset = model.objects.all()

        if start_date:
            queryset = queryset.filter(datum__gte=start_date)
        if end_date:
            queryset = queryset.filter(datum__lte=end_date)

        # Order by timestamp and limit
        queryset = queryset.order_by('timestamp')[:limit]

        # Serialize
        serializer = OHLCVSerializer(queryset, many=True)

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

        # Query parameters
        indicator_type = request.GET.get('indicator', 'rsi').lower()
        period = int(request.GET.get('period', 14 if indicator_type == 'rsi' else 20))
        limit = int(request.GET.get('limit', 500))

        # Fetch OHLCV data
        queryset = model.objects.order_by('timestamp')[:limit]

        if not queryset:
            return Response(
                {'error': 'No data available'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Convert to DataFrame
        data = list(queryset.values('timestamp', 'open', 'high', 'low', 'close', 'volume'))
        df = pd.DataFrame(data)

        # Calculate indicator
        calc = TechnicalIndicators()

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

        else:
            return Response(
                {'error': f'Unknown indicator: {indicator_type}'},
                status=status.HTTP_400_BAD_REQUEST
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
