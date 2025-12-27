"""
Django REST Framework Serializers for Bitcoin Trading Data

Serializers convert Django model instances and Python datatypes
to/from JSON for the REST API.
"""

from rest_framework import serializers


class OHLCVSerializer(serializers.Serializer):
    """
    Serializer for OHLCV candlestick data.

    TradingView Lightweight Charts expects data in this format:
    { time: <unix_seconds>, open: <float>, high: <float>, low: <float>, close: <float> }
    """

    time = serializers.SerializerMethodField()
    open = serializers.FloatField()
    high = serializers.FloatField()
    low = serializers.FloatField()
    close = serializers.FloatField()
    volume = serializers.FloatField()

    def get_time(self, obj):
        """Convert timestamp from milliseconds to seconds (TradingView format)"""
        return obj.timestamp // 1000


class IndicatorSerializer(serializers.Serializer):
    """
    Serializer for single-line technical indicators (RSI, SMA, EMA).

    Format: { time: <unix_seconds>, value: <float> }
    """

    time = serializers.IntegerField()
    value = serializers.FloatField()


class BollingerBandsSerializer(serializers.Serializer):
    """
    Serializer for Bollinger Bands (3 lines: upper, middle, lower).

    Format: { time: <unix_seconds>, upper: <float>, middle: <float>, lower: <float> }
    """

    time = serializers.IntegerField()
    upper = serializers.FloatField()
    middle = serializers.FloatField()
    lower = serializers.FloatField()


class LatestPriceSerializer(serializers.Serializer):
    """
    Serializer for latest price information.

    Includes timeframe, timestamp, human-readable date, closing price,
    and percentage change from previous candle.
    """

    timeframe = serializers.CharField()
    timestamp = serializers.IntegerField()
    datum = serializers.CharField()
    close = serializers.FloatField()
    change_percent = serializers.FloatField(allow_null=True)
