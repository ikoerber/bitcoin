"""
Tests for Bitcoin Trading Dashboard

Includes tests for:
- Trading Performance Analysis
- API endpoints
- FIFO P&L calculation
- BNB fee conversion
"""

from django.test import TestCase, Client
from django.conf import settings
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import json

from charts.trading_performance import TradingPerformanceAnalyzer


class TradingPerformanceAnalyzerTests(TestCase):
    """Test the TradingPerformanceAnalyzer class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock API keys for testing
        self.original_api_key = settings.BINANCE_API_KEY
        self.original_api_secret = settings.BINANCE_API_SECRET

        settings.BINANCE_API_KEY = 'test_api_key'
        settings.BINANCE_API_SECRET = 'test_api_secret'

    def tearDown(self):
        """Restore original settings."""
        settings.BINANCE_API_KEY = self.original_api_key
        settings.BINANCE_API_SECRET = self.original_api_secret

    @patch('charts.trading_performance.ccxt.binance')
    def test_analyzer_initialization(self, mock_binance):
        """Test that analyzer initializes correctly with API keys."""
        analyzer = TradingPerformanceAnalyzer()

        # Check that binance was initialized
        mock_binance.assert_called_once()
        call_kwargs = mock_binance.call_args[0][0]

        self.assertEqual(call_kwargs['apiKey'], 'test_api_key')
        self.assertEqual(call_kwargs['secret'], 'test_api_secret')
        self.assertTrue(call_kwargs['enableRateLimit'])

    def test_analyzer_requires_api_keys(self):
        """Test that analyzer raises error without API keys."""
        settings.BINANCE_API_KEY = ''
        settings.BINANCE_API_SECRET = ''

        with self.assertRaises(ValueError) as context:
            TradingPerformanceAnalyzer()

        self.assertIn('API keys not configured', str(context.exception))

    @patch('charts.trading_performance.ccxt.binance')
    def test_get_bnb_eur_price(self, mock_binance):
        """Test BNB/EUR price fetching."""
        # Mock the exchange
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.return_value = {'last': 610.50}
        mock_binance.return_value = mock_exchange

        analyzer = TradingPerformanceAnalyzer()
        price = analyzer.get_current_bnb_eur_price()

        self.assertEqual(price, 610.50)
        mock_exchange.fetch_ticker.assert_called_once_with('BNB/EUR')

    @patch('charts.trading_performance.ccxt.binance')
    def test_get_bnb_eur_price_fallback(self, mock_binance):
        """Test BNB/EUR price fallback calculation via USDT."""
        # Mock the exchange
        mock_exchange = MagicMock()

        # BNB/EUR fails, use fallback
        def fetch_ticker_side_effect(symbol):
            if symbol == 'BNB/EUR':
                raise Exception("Pair not available")
            elif symbol == 'BNB/USDT':
                return {'last': 600.0}
            elif symbol == 'EUR/USDT':
                return {'last': 1.05}

        mock_exchange.fetch_ticker.side_effect = fetch_ticker_side_effect
        mock_binance.return_value = mock_exchange

        analyzer = TradingPerformanceAnalyzer()
        price = analyzer.get_current_bnb_eur_price()

        # BNB/EUR = BNB/USDT * EUR/USDT = 600 * 1.05 = 630
        self.assertEqual(price, 630.0)

    @patch('charts.trading_performance.ccxt.binance')
    def test_fetch_trade_history(self, mock_binance):
        """Test fetching trade history."""
        # Mock trades data
        mock_trades = [
            {
                'id': '1',
                'timestamp': 1609459200000,  # 2021-01-01
                'symbol': 'BTC/EUR',
                'side': 'buy',
                'price': 25000.0,
                'amount': 0.1,
                'cost': 2500.0,
                'fee': {'currency': 'BNB', 'cost': 0.001}
            },
            {
                'id': '2',
                'timestamp': 1609545600000,  # 2021-01-02
                'symbol': 'BTC/EUR',
                'side': 'sell',
                'price': 26000.0,
                'amount': 0.1,
                'cost': 2600.0,
                'fee': {'currency': 'BNB', 'cost': 0.001}
            }
        ]

        mock_exchange = MagicMock()
        mock_exchange.fetch_my_trades.return_value = mock_trades
        mock_binance.return_value = mock_exchange

        analyzer = TradingPerformanceAnalyzer()
        since = datetime(2021, 1, 1)
        trades = analyzer.fetch_trade_history(symbol='BTC/EUR', since=since, limit=100)

        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0]['side'], 'buy')
        self.assertEqual(trades[1]['side'], 'sell')

    def test_fifo_pnl_calculation(self):
        """Test FIFO P&L calculation logic."""
        # Create mock analyzer (without API calls)
        with patch('charts.trading_performance.ccxt.binance'):
            settings.BINANCE_API_KEY = 'test'
            settings.BINANCE_API_SECRET = 'test'
            analyzer = TradingPerformanceAnalyzer()

        # Simple case: 1 buy, 1 sell
        buy_trades = [
            {
                'amount': Decimal('0.1'),
                'price': Decimal('50000'),
                'cost': Decimal('5000'),
                'timestamp': 1000
            }
        ]

        sell_trades = [
            {
                'amount': Decimal('0.1'),
                'price': Decimal('52000'),
                'cost': Decimal('5200'),
                'timestamp': 2000
            }
        ]

        pnl = analyzer._calculate_fifo_pnl(buy_trades, sell_trades)

        # P&L = 0.1 * (52000 - 50000) = 200
        self.assertEqual(pnl, Decimal('200'))

    def test_fifo_pnl_partial_match(self):
        """Test FIFO P&L with partial position matching."""
        with patch('charts.trading_performance.ccxt.binance'):
            settings.BINANCE_API_KEY = 'test'
            settings.BINANCE_API_SECRET = 'test'
            analyzer = TradingPerformanceAnalyzer()

        # Buy 0.2 BTC in two trades
        buy_trades = [
            {
                'amount': Decimal('0.1'),
                'price': Decimal('50000'),
                'cost': Decimal('5000'),
                'timestamp': 1000
            },
            {
                'amount': Decimal('0.1'),
                'price': Decimal('51000'),
                'cost': Decimal('5100'),
                'timestamp': 1500
            }
        ]

        # Sell 0.15 BTC (partially closes both buys)
        sell_trades = [
            {
                'amount': Decimal('0.15'),
                'price': Decimal('53000'),
                'cost': Decimal('7950'),
                'timestamp': 2000
            }
        ]

        pnl = analyzer._calculate_fifo_pnl(buy_trades, sell_trades)

        # First 0.1 BTC: (53000 - 50000) * 0.1 = 300
        # Next 0.05 BTC: (53000 - 51000) * 0.05 = 100
        # Total P&L = 400
        self.assertEqual(pnl, Decimal('400'))

    @patch('charts.trading_performance.ccxt.binance')
    def test_calculate_performance_metrics(self, mock_binance):
        """Test comprehensive performance metrics calculation."""
        mock_exchange = MagicMock()
        mock_binance.return_value = mock_exchange

        analyzer = TradingPerformanceAnalyzer()

        # Mock trades with BNB fees
        trades = [
            {
                'amount': 0.1,
                'price': 50000.0,
                'cost': 5000.0,
                'side': 'buy',
                'timestamp': 1000,
                'fee': {'currency': 'BNB', 'cost': 0.01}
            },
            {
                'amount': 0.1,
                'price': 52000.0,
                'cost': 5200.0,
                'side': 'sell',
                'timestamp': 2000,
                'fee': {'currency': 'BNB', 'cost': 0.01}
            }
        ]

        bnb_eur_price = 600.0  # 1 BNB = 600 EUR

        metrics = analyzer.calculate_performance_metrics(trades, bnb_eur_price)

        # Verify basic counts
        self.assertEqual(metrics['total_trades'], 2)
        self.assertEqual(metrics['buy_trades'], 1)
        self.assertEqual(metrics['sell_trades'], 1)

        # Verify fees
        # Total BNB fees: 0.01 + 0.01 = 0.02 BNB
        # In EUR: 0.02 * 600 = 12 EUR
        self.assertEqual(metrics['total_fees_bnb'], 0.02)
        self.assertEqual(metrics['total_fees_eur'], 12.0)

        # Verify P&L
        # Buy: 0.1 BTC @ 50000 = 5000 EUR
        # Sell: 0.1 BTC @ 52000 = 5200 EUR
        # P&L: 200 EUR
        # Net P&L: 200 - 12 = 188 EUR
        self.assertEqual(metrics['realized_pnl_eur'], 200.0)
        self.assertEqual(metrics['realized_pnl_net_eur'], 188.0)

    @patch('charts.trading_performance.ccxt.binance')
    def test_get_account_balance(self, mock_binance):
        """Test account balance fetching."""
        mock_exchange = MagicMock()
        mock_exchange.fetch_balance.return_value = {
            'BTC': {'free': 0.05, 'used': 0.01, 'total': 0.06},
            'EUR': {'free': 1000.0, 'used': 500.0, 'total': 1500.0},
            'BNB': {'free': 0.5, 'used': 0.0, 'total': 0.5}
        }
        mock_binance.return_value = mock_exchange

        analyzer = TradingPerformanceAnalyzer()
        balance = analyzer.get_account_balance()

        self.assertEqual(balance['btc']['total'], 0.06)
        self.assertEqual(balance['eur']['total'], 1500.0)
        self.assertEqual(balance['bnb']['total'], 0.5)


class TradingPerformanceAPITests(TestCase):
    """Test the /api/trading-performance/ endpoint."""

    def setUp(self):
        """Set up test client and mock API keys."""
        self.client = Client()
        self.original_api_key = settings.BINANCE_API_KEY
        self.original_api_secret = settings.BINANCE_API_SECRET

        settings.BINANCE_API_KEY = 'test_api_key'
        settings.BINANCE_API_SECRET = 'test_api_secret'

    def tearDown(self):
        """Restore original settings."""
        settings.BINANCE_API_KEY = self.original_api_key
        settings.BINANCE_API_SECRET = self.original_api_secret

    def test_api_requires_keys(self):
        """Test that API returns error without keys."""
        settings.BINANCE_API_KEY = ''
        settings.BINANCE_API_SECRET = ''

        response = self.client.get('/api/trading-performance/')

        self.assertEqual(response.status_code, 503)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('API keys not configured', data['error'])

    def test_api_validates_days_parameter(self):
        """Test days parameter validation."""
        # Invalid: non-integer
        response = self.client.get('/api/trading-performance/?days=invalid')
        self.assertEqual(response.status_code, 400)

        # Invalid: too small
        response = self.client.get('/api/trading-performance/?days=0')
        self.assertEqual(response.status_code, 400)

        # Invalid: too large
        response = self.client.get('/api/trading-performance/?days=400')
        self.assertEqual(response.status_code, 400)

    @patch('charts.views.TradingPerformanceAnalyzer')
    def test_api_success_response(self, mock_analyzer_class):
        """Test successful API response structure."""
        # Mock analyzer instance
        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock trade history
        mock_analyzer.fetch_trade_history.return_value = [
            {
                'amount': 0.1,
                'price': 50000.0,
                'cost': 5000.0,
                'side': 'buy',
                'timestamp': 1000,
                'fee': {'currency': 'BNB', 'cost': 0.01}
            }
        ]

        # Mock BNB price
        mock_analyzer.get_current_bnb_eur_price.return_value = 600.0

        # Mock metrics
        mock_analyzer.calculate_performance_metrics.return_value = {
            'total_trades': 1,
            'buy_trades': 1,
            'sell_trades': 0,
            'total_fees_eur': 6.0,
            'realized_pnl_eur': 0.0,
            'roi': 0.0
        }

        # Mock balance
        mock_analyzer.get_account_balance.return_value = {
            'btc': {'free': 0.1, 'used': 0, 'total': 0.1},
            'eur': {'free': 1000, 'used': 0, 'total': 1000},
            'bnb': {'free': 0.5, 'used': 0, 'total': 0.5}
        }

        response = self.client.get('/api/trading-performance/?days=30')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verify response structure
        self.assertIn('period', data)
        self.assertIn('metrics', data)
        self.assertIn('balance', data)
        self.assertIn('timestamp', data)

        # Verify period
        self.assertEqual(data['period']['days'], 30)

        # Verify metrics
        self.assertEqual(data['metrics']['total_trades'], 1)

        # Verify balance
        self.assertEqual(data['balance']['btc']['total'], 0.1)

    @patch('charts.views.TradingPerformanceAnalyzer')
    def test_api_no_trades_response(self, mock_analyzer_class):
        """Test API response when no trades found."""
        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Return empty trade list
        mock_analyzer.fetch_trade_history.return_value = []

        response = self.client.get('/api/trading-performance/?days=90')

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['total_trades'], 0)
        self.assertIn('message', data)

    @patch('charts.views.TradingPerformanceAnalyzer')
    def test_api_handles_exchange_errors(self, mock_analyzer_class):
        """Test API error handling for exchange errors."""
        mock_analyzer = MagicMock()
        mock_analyzer_class.return_value = mock_analyzer

        # Simulate exchange error
        mock_analyzer.fetch_trade_history.side_effect = Exception("Exchange API error")

        response = self.client.get('/api/trading-performance/')

        self.assertEqual(response.status_code, 500)
        data = json.loads(response.content)
        self.assertIn('error', data)


class FIFOAlgorithmTests(TestCase):
    """Detailed tests for FIFO matching algorithm."""

    def setUp(self):
        """Set up analyzer for FIFO tests."""
        with patch('charts.trading_performance.ccxt.binance'):
            settings.BINANCE_API_KEY = 'test'
            settings.BINANCE_API_SECRET = 'test'
            self.analyzer = TradingPerformanceAnalyzer()

    def test_fifo_simple_profit(self):
        """Test simple profitable trade."""
        buys = [{'amount': Decimal('1.0'), 'price': Decimal('100'), 'timestamp': 1}]
        sells = [{'amount': Decimal('1.0'), 'price': Decimal('110'), 'timestamp': 2}]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        self.assertEqual(pnl, Decimal('10'))  # 1.0 * (110 - 100)

    def test_fifo_simple_loss(self):
        """Test simple losing trade."""
        buys = [{'amount': Decimal('1.0'), 'price': Decimal('100'), 'timestamp': 1}]
        sells = [{'amount': Decimal('1.0'), 'price': Decimal('90'), 'timestamp': 2}]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        self.assertEqual(pnl, Decimal('-10'))  # 1.0 * (90 - 100)

    def test_fifo_multiple_buys_single_sell(self):
        """Test FIFO with multiple buys matched to one sell."""
        buys = [
            {'amount': Decimal('0.5'), 'price': Decimal('100'), 'timestamp': 1},
            {'amount': Decimal('0.5'), 'price': Decimal('105'), 'timestamp': 2}
        ]
        sells = [{'amount': Decimal('1.0'), 'price': Decimal('110'), 'timestamp': 3}]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        # First 0.5: (110 - 100) * 0.5 = 5
        # Second 0.5: (110 - 105) * 0.5 = 2.5
        # Total: 7.5
        self.assertEqual(pnl, Decimal('7.5'))

    def test_fifo_order_matters(self):
        """Test that FIFO order is respected."""
        # Scenario: Buy low, buy high, sell at mid price
        buys = [
            {'amount': Decimal('1.0'), 'price': Decimal('100'), 'timestamp': 1},
            {'amount': Decimal('1.0'), 'price': Decimal('120'), 'timestamp': 2}
        ]
        sells = [{'amount': Decimal('1.0'), 'price': Decimal('110'), 'timestamp': 3}]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        # FIFO: First buy @ 100 is matched first
        # P&L = 1.0 * (110 - 100) = 10
        self.assertEqual(pnl, Decimal('10'))

    def test_fifo_remaining_position(self):
        """Test FIFO with remaining unmatched position."""
        buys = [
            {'amount': Decimal('2.0'), 'price': Decimal('100'), 'timestamp': 1}
        ]
        sells = [
            {'amount': Decimal('1.0'), 'price': Decimal('110'), 'timestamp': 2}
        ]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        # Only 1.0 is sold, 1.0 remains
        # P&L = 1.0 * (110 - 100) = 10
        self.assertEqual(pnl, Decimal('10'))

    def test_fifo_no_sells(self):
        """Test FIFO with no sells (all positions open)."""
        buys = [
            {'amount': Decimal('1.0'), 'price': Decimal('100'), 'timestamp': 1}
        ]
        sells = []

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        self.assertEqual(pnl, Decimal('0'))  # No realized P&L

    def test_fifo_empty_buys(self):
        """Test FIFO with sells but no buys (shouldn't happen normally)."""
        buys = []
        sells = [
            {'amount': Decimal('1.0'), 'price': Decimal('100'), 'timestamp': 1}
        ]

        pnl = self.analyzer._calculate_fifo_pnl(buys, sells)
        self.assertEqual(pnl, Decimal('0'))  # No P&L without matching buys
