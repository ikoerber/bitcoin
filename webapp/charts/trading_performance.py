"""
Trading Performance Analysis Module

Analyzes personal trading performance from Binance account data.
Calculates P&L, win-rate, ROI, and fee analysis with BNB conversion to EUR.
"""

import ccxt
from decimal import Decimal
from typing import List, Dict, Any
from datetime import datetime, timedelta
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TradingPerformanceAnalyzer:
    """
    Analyzes trading performance from Binance account.

    Features:
    - Fetches trade history for BTC/EUR pair
    - Calculates P&L including BNB fees converted to EUR
    - Computes win-rate, ROI, and other metrics
    """

    def __init__(self):
        """Initialize Binance API connection with read-only keys."""
        if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
            raise ValueError(
                "Binance API keys not configured. "
                "Set BINANCE_API_KEY and BINANCE_API_SECRET in environment variables."
            )

        self.exchange = ccxt.binance({
            'apiKey': settings.BINANCE_API_KEY,
            'secret': settings.BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Spot trading only
            }
        })

        logger.info("Trading Performance Analyzer initialized with Binance API")

    def get_current_bnb_eur_price(self) -> float:
        """
        Get current BNB/EUR price from Binance.

        Returns:
            Current BNB price in EUR
        """
        try:
            ticker = self.exchange.fetch_ticker('BNB/EUR')
            price = float(ticker['last'])
            logger.info(f"Current BNB/EUR price: {price:.2f} EUR")
            return price
        except Exception as e:
            logger.error(f"Error fetching BNB/EUR price: {e}")
            # Fallback: try to get BNB/EUR via BNB/USDT * USDT/EUR
            try:
                bnb_usdt = self.exchange.fetch_ticker('BNB/USDT')
                usdt_eur = self.exchange.fetch_ticker('EUR/USDT')

                bnb_price_usdt = float(bnb_usdt['last'])
                eur_price_usdt = float(usdt_eur['last'])

                # BNB/EUR = BNB/USDT * EUR/USDT
                bnb_eur = bnb_price_usdt * eur_price_usdt
                logger.info(f"Calculated BNB/EUR price via USDT: {bnb_eur:.2f} EUR")
                return bnb_eur
            except Exception as e2:
                logger.error(f"Fallback BNB price calculation failed: {e2}")
                raise

    def fetch_trade_history(
        self,
        symbol: str = 'BTC/EUR',
        since: datetime = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch trade history from Binance.

        Args:
            symbol: Trading pair (default: BTC/EUR)
            since: Start date for trades (default: last 90 days)
            limit: Maximum number of trades to fetch

        Returns:
            List of trades with details
        """
        if since is None:
            since = datetime.now() - timedelta(days=90)

        since_timestamp = int(since.timestamp() * 1000)  # Convert to ms

        try:
            logger.info(f"Fetching trade history for {symbol} since {since.isoformat()}")
            trades = self.exchange.fetch_my_trades(
                symbol=symbol,
                since=since_timestamp,
                limit=limit
            )

            logger.info(f"Fetched {len(trades)} trades for {symbol}")
            return trades

        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            raise

    def calculate_performance_metrics(
        self,
        trades: List[Dict[str, Any]],
        bnb_eur_price: float = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive trading performance metrics.

        Args:
            trades: List of trades from fetch_trade_history()
            bnb_eur_price: Current BNB/EUR price (fetched if not provided)

        Returns:
            Dictionary with performance metrics:
            - total_trades: Total number of trades
            - buy_trades: Number of buy trades
            - sell_trades: Number of sell trades
            - total_volume_btc: Total BTC volume traded
            - total_volume_eur: Total EUR volume traded
            - total_fees_bnb: Total fees paid in BNB
            - total_fees_eur: Total fees in EUR (converted from BNB)
            - realized_pnl_eur: Realized profit/loss in EUR
            - win_rate: Percentage of profitable trades
            - avg_trade_size_eur: Average trade size in EUR
            - roi: Return on investment percentage
        """
        if not trades:
            return {
                'total_trades': 0,
                'error': 'No trades found'
            }

        # Get current BNB price if not provided
        if bnb_eur_price is None:
            bnb_eur_price = self.get_current_bnb_eur_price()

        buy_trades = []
        sell_trades = []
        total_fees_bnb = Decimal('0')
        total_volume_btc = Decimal('0')
        total_volume_eur = Decimal('0')

        for trade in trades:
            amount_btc = Decimal(str(trade['amount']))  # BTC amount
            price_eur = Decimal(str(trade['price']))  # Price in EUR
            cost_eur = Decimal(str(trade['cost']))  # Total cost in EUR

            total_volume_btc += amount_btc
            total_volume_eur += cost_eur

            # Fee handling (BNB fees)
            fee = trade.get('fee', {})
            if fee and fee.get('currency') == 'BNB':
                fee_amount = Decimal(str(fee['cost']))
                total_fees_bnb += fee_amount

            # Categorize trades
            if trade['side'] == 'buy':
                buy_trades.append({
                    'amount': amount_btc,
                    'price': price_eur,
                    'cost': cost_eur,
                    'timestamp': trade['timestamp']
                })
            else:  # sell
                sell_trades.append({
                    'amount': amount_btc,
                    'price': price_eur,
                    'cost': cost_eur,
                    'timestamp': trade['timestamp']
                })

        # Convert BNB fees to EUR
        total_fees_eur = float(total_fees_bnb) * bnb_eur_price

        # Calculate P&L using FIFO matching
        realized_pnl_eur = self._calculate_fifo_pnl(buy_trades, sell_trades)

        # Calculate win-rate (simple approach: compare avg buy vs avg sell price)
        avg_buy_price = (
            sum(t['price'] for t in buy_trades) / len(buy_trades)
            if buy_trades else Decimal('0')
        )
        avg_sell_price = (
            sum(t['price'] for t in sell_trades) / len(sell_trades)
            if sell_trades else Decimal('0')
        )

        win_rate = 0.0
        if avg_buy_price > 0 and avg_sell_price > 0:
            win_rate = float((avg_sell_price / avg_buy_price - 1) * 100)

        # Calculate ROI
        total_investment = sum(t['cost'] for t in buy_trades)
        roi = 0.0
        if total_investment > 0:
            roi = float((realized_pnl_eur / total_investment) * 100)

        return {
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_volume_btc': float(total_volume_btc),
            'total_volume_eur': float(total_volume_eur),
            'total_fees_bnb': float(total_fees_bnb),
            'total_fees_eur': round(total_fees_eur, 2),
            'bnb_eur_rate': round(bnb_eur_price, 2),
            'realized_pnl_eur': round(float(realized_pnl_eur), 2),
            'realized_pnl_net_eur': round(float(realized_pnl_eur) - total_fees_eur, 2),
            'win_rate': round(win_rate, 2),
            'avg_buy_price': float(avg_buy_price),
            'avg_sell_price': float(avg_sell_price),
            'avg_trade_size_eur': round(float(total_volume_eur / len(trades)), 2),
            'roi': round(roi, 2),
            'roi_net': round(roi - (total_fees_eur / float(total_investment) * 100), 2) if total_investment > 0 else 0.0,
        }

    def _calculate_fifo_pnl(
        self,
        buy_trades: List[Dict],
        sell_trades: List[Dict]
    ) -> Decimal:
        """
        Calculate realized P&L using FIFO (First-In-First-Out) matching.

        Args:
            buy_trades: List of buy trades
            sell_trades: List of sell trades

        Returns:
            Realized profit/loss in EUR
        """
        # Sort by timestamp
        buys = sorted(buy_trades, key=lambda x: x['timestamp'])
        sells = sorted(sell_trades, key=lambda x: x['timestamp'])

        buy_queue = buys.copy()
        realized_pnl = Decimal('0')

        for sell in sells:
            sell_amount_remaining = sell['amount']
            sell_price = sell['price']

            while sell_amount_remaining > 0 and buy_queue:
                buy = buy_queue[0]
                buy_amount = buy['amount']
                buy_price = buy['price']

                # Match amount
                matched_amount = min(sell_amount_remaining, buy_amount)

                # Calculate P&L for this match
                pnl = matched_amount * (sell_price - buy_price)
                realized_pnl += pnl

                # Update remaining amounts
                sell_amount_remaining -= matched_amount
                buy['amount'] -= matched_amount

                # Remove fully matched buy
                if buy['amount'] <= 0:
                    buy_queue.pop(0)

        return realized_pnl

    def calculate_daily_performance(
        self,
        trades: List[Dict[str, Any]],
        bnb_eur_price: float = None
    ) -> List[Dict[str, Any]]:
        """
        Calculate daily trading performance metrics grouped by day.

        Args:
            trades: List of trades from fetch_trade_history()
            bnb_eur_price: Current BNB/EUR price (fetched if not provided)

        Returns:
            List of daily metrics, each containing:
            - date: Date string (YYYY-MM-DD)
            - total_trades: Number of trades on this day
            - volume_btc: BTC volume traded
            - volume_eur: EUR volume traded
            - fees_bnb: Fees in BNB
            - fees_eur: Fees in EUR (converted)
            - realized_pnl_eur: Realized P&L for this day (FIFO)
        """
        if not trades:
            return []

        # Get current BNB price if not provided
        if bnb_eur_price is None:
            bnb_eur_price = self.get_current_bnb_eur_price()

        # Group trades by date
        from collections import defaultdict
        daily_data = defaultdict(lambda: {
            'buy_trades': [],
            'sell_trades': [],
            'fees_bnb': Decimal('0'),
            'volume_btc': Decimal('0'),
            'volume_eur': Decimal('0'),
        })

        for trade in trades:
            # Convert timestamp to date
            trade_date = datetime.fromtimestamp(trade['timestamp'] / 1000).date()
            date_str = trade_date.strftime('%Y-%m-%d')

            amount_btc = Decimal(str(trade['amount']))
            price_eur = Decimal(str(trade['price']))
            cost_eur = Decimal(str(trade['cost']))

            daily_data[date_str]['volume_btc'] += amount_btc
            daily_data[date_str]['volume_eur'] += cost_eur

            # Fee handling
            fee = trade.get('fee', {})
            if fee and fee.get('currency') == 'BNB':
                fee_amount = Decimal(str(fee['cost']))
                daily_data[date_str]['fees_bnb'] += fee_amount

            # Categorize trades
            trade_info = {
                'amount': amount_btc,
                'price': price_eur,
                'cost': cost_eur,
                'timestamp': trade['timestamp']
            }

            if trade['side'] == 'buy':
                daily_data[date_str]['buy_trades'].append(trade_info)
            else:
                daily_data[date_str]['sell_trades'].append(trade_info)

        # Calculate metrics for each day
        result = []
        for date_str in sorted(daily_data.keys()):
            day_info = daily_data[date_str]

            # Calculate P&L for this day using FIFO
            realized_pnl = self._calculate_fifo_pnl(
                day_info['buy_trades'],
                day_info['sell_trades']
            )

            fees_eur = float(day_info['fees_bnb']) * bnb_eur_price
            total_trades = len(day_info['buy_trades']) + len(day_info['sell_trades'])

            result.append({
                'date': date_str,
                'total_trades': total_trades,
                'volume_btc': round(float(day_info['volume_btc']), 8),
                'volume_eur': round(float(day_info['volume_eur']), 2),
                'fees_bnb': round(float(day_info['fees_bnb']), 8),
                'fees_eur': round(fees_eur, 2),
                'realized_pnl_eur': round(float(realized_pnl), 2),
                'realized_pnl_net_eur': round(float(realized_pnl) - fees_eur, 2),
            })

        return result

    def get_account_balance(self) -> Dict[str, Any]:
        """
        Get current account balances.

        Returns:
            Dictionary with BTC and EUR balances
        """
        try:
            balance = self.exchange.fetch_balance()

            btc_balance = balance.get('BTC', {})
            eur_balance = balance.get('EUR', {})
            bnb_balance = balance.get('BNB', {})

            return {
                'btc': {
                    'free': float(btc_balance.get('free', 0)),
                    'used': float(btc_balance.get('used', 0)),
                    'total': float(btc_balance.get('total', 0)),
                },
                'eur': {
                    'free': float(eur_balance.get('free', 0)),
                    'used': float(eur_balance.get('used', 0)),
                    'total': float(eur_balance.get('total', 0)),
                },
                'bnb': {
                    'free': float(bnb_balance.get('free', 0)),
                    'used': float(bnb_balance.get('used', 0)),
                    'total': float(bnb_balance.get('total', 0)),
                }
            }
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            raise
