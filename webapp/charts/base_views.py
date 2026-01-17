"""
Base view classes for the charts application.

Provides reusable view classes with common patterns for:
- Binance API synchronization operations
- Data validation and error handling
- Consistent response formatting
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .utils import require_binance_api_keys, error_response, success_response
from .trading_performance import TradingPerformanceAnalyzer

logger = logging.getLogger(__name__)


class BinanceSyncBaseView(APIView):
    """
    Base view for Binance synchronization operations.

    Provides common functionality for sync views:
    - API key validation (via decorator)
    - Trading performance analyzer initialization
    - Error handling
    - Response formatting

    Subclasses must implement:
    - sync_method_name: str - Name of the sync method to call
    - get_sync_params(request): dict - Extract sync parameters from request
    """

    sync_method_name = None  # Must be overridden by subclass

    @require_binance_api_keys
    def get(self, request):
        """
        Handle GET request for synchronization.

        Returns:
            Response: Sync results or error message
        """
        if self.sync_method_name is None:
            return error_response(
                'Sync method not defined',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        try:
            # Get sync parameters from subclass
            sync_params = self.get_sync_params(request)

            # Initialize analyzer
            analyzer = TradingPerformanceAnalyzer()

            # Get sync method from analyzer
            sync_method = getattr(analyzer, self.sync_method_name)

            # Log sync operation
            logger.info(f'Starting {self.sync_method_name} with params: {sync_params}')

            # Perform sync
            result = sync_method(**sync_params)

            # Log result
            logger.info(f'{self.sync_method_name} complete: {result}')

            # Return success response
            return success_response(result)

        except ValueError as e:
            # Parameter validation error
            return error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Unexpected error
            logger.error(f'Error in {self.sync_method_name}: {str(e)}', exc_info=True)
            return error_response(
                f'Error during synchronization: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_sync_params(self, request):
        """
        Extract synchronization parameters from request.

        Must be implemented by subclass.

        Args:
            request: Django request object

        Returns:
            dict: Parameters for sync method
        """
        raise NotImplementedError('Subclass must implement get_sync_params()')


class TimeframeValidatedView(APIView):
    """
    Base view that validates timeframe parameter.

    Provides common functionality for views that work with timeframes:
    - Timeframe validation
    - Model retrieval
    - Error handling
    """

    def get_validated_timeframe_and_model(self, timeframe):
        """
        Validate timeframe and return corresponding model.

        Args:
            timeframe: Timeframe string (15m, 1h, 4h, 1d)

        Returns:
            tuple: (timeframe, model) or (None, error_response)
        """
        from .models import TIMEFRAME_MODELS

        if timeframe not in TIMEFRAME_MODELS:
            return None, error_response(
                f'Invalid timeframe: {timeframe}',
                valid_timeframes=list(TIMEFRAME_MODELS.keys())
            )

        model = TIMEFRAME_MODELS[timeframe]
        return model, None


class PaginatedQueryView(APIView):
    """
    Base view for paginated database queries.

    Provides common functionality for views that query paginated data:
    - Limit parameter extraction and validation
    - Consistent error handling
    """

    default_limit = 500
    max_limit = 10000

    def get_validated_limit(self, request):
        """
        Extract and validate limit parameter from request.

        Args:
            request: Django request object

        Returns:
            tuple: (limit, error_response) - error_response is None if successful
        """
        from .utils import get_limit_param
        return get_limit_param(request, self.default_limit, self.max_limit)
