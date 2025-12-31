"""
Trading Performance Analysis Module

Analyzes personal trading performance from Binance account data.
Calculates P&L, win-rate, ROI, and fee analysis with BNB conversion to EUR.
"""

import ccxt
from decimal import Decimal
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import logging
import sqlite3

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

    def sync_trades_to_database(
        self,
        symbol: str = 'BTC/EUR',
        since: Optional[datetime] = None,
        db_path: str = None
    ) -> Dict[str, Any]:
        """
        Synchronize trades from Binance API to local SQLite database.

        This function:
        1. Checks the most recent trade in the database
        2. Fetches only new trades from Binance API (incremental sync)
        3. Stores them in the btc_eur_trades table
        4. Avoids duplicates using trade_id as primary key

        Args:
            symbol: Trading pair (default: BTC/EUR)
            since: Start date for sync (default: fetch all trades after latest in DB)
            db_path: Path to SQLite database (default: btc_eur_data.db in project root)

        Returns:
            Dictionary with sync statistics:
            - trades_synced: Number of new trades added
            - latest_trade_timestamp: Timestamp of most recent trade
            - total_trades_in_db: Total trades in database after sync
        """
        import os

        if db_path is None:
            # Default: btc_eur_data.db in project root (one level up from webapp/)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'btc_eur_data.db')

        logger.info(f"Starting trade synchronization for {symbol}")
        logger.info(f"Database path: {db_path}")

        # Connect to database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get the timestamp of the most recent trade in database
            cursor.execute(
                "SELECT MAX(timestamp) FROM btc_eur_trades WHERE symbol = ?",
                (symbol,)
            )
            result = cursor.fetchone()
            latest_timestamp_ms = result[0] if result[0] else None

            # Determine starting point for API fetch
            if since:
                since_timestamp_ms = int(since.timestamp() * 1000)
            elif latest_timestamp_ms:
                # Fetch trades since last sync (add 1ms to avoid duplicate)
                since_timestamp_ms = latest_timestamp_ms + 1
                logger.info(f"Incremental sync: fetching trades since {datetime.fromtimestamp(since_timestamp_ms / 1000)}")
            else:
                # No trades in DB yet, fetch from beginning (default: 1 year ago)
                since = datetime.now() - timedelta(days=365)
                since_timestamp_ms = int(since.timestamp() * 1000)
                logger.info(f"Initial sync: fetching all trades since {since}")

            # Fetch trades from Binance API
            try:
                logger.info(f"Fetching trades from Binance API (since timestamp: {since_timestamp_ms})")
                trades = self.exchange.fetch_my_trades(
                    symbol=symbol,
                    since=since_timestamp_ms,
                    limit=1000  # Binance limit
                )

                logger.info(f"Fetched {len(trades)} trades from Binance API")

                # Insert trades into database (ignore duplicates)
                trades_synced = 0
                for trade in trades:
                    try:
                        cursor.execute("""
                            INSERT OR IGNORE INTO btc_eur_trades (
                                trade_id, order_id, symbol, timestamp, datetime,
                                side, price, amount, cost,
                                fee_cost, fee_currency, is_maker
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            str(trade['id']),  # trade_id
                            str(trade['order']),  # order_id
                            trade['symbol'],  # symbol
                            trade['timestamp'],  # timestamp (ms)
                            datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),  # datetime
                            trade['side'],  # side (buy/sell)
                            float(trade['price']),  # price
                            float(trade['amount']),  # amount
                            float(trade['cost']),  # cost
                            float(trade['fee']['cost']),  # fee_cost
                            trade['fee']['currency'],  # fee_currency
                            1 if trade.get('maker', False) else 0  # is_maker
                        ))

                        if cursor.rowcount > 0:
                            trades_synced += 1

                    except Exception as e:
                        logger.warning(f"Failed to insert trade {trade['id']}: {e}")
                        continue

                conn.commit()

                # Get statistics
                cursor.execute("SELECT COUNT(*), MAX(timestamp) FROM btc_eur_trades WHERE symbol = ?", (symbol,))
                total_trades, latest_timestamp = cursor.fetchone()

                logger.info(f"Sync complete: {trades_synced} new trades added, {total_trades} total in database")

                return {
                    'trades_synced': trades_synced,
                    'trades_fetched_from_api': len(trades),
                    'latest_trade_timestamp': latest_timestamp,
                    'latest_trade_datetime': datetime.fromtimestamp(latest_timestamp / 1000).isoformat() if latest_timestamp else None,
                    'total_trades_in_db': total_trades,
                    'symbol': symbol,
                    'sync_timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error during trade synchronization: {e}")
                raise

    def get_trades_from_database(
        self,
        symbol: str = 'BTC/EUR',
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        db_path: str = None
    ) -> List[Dict[str, Any]]:
        """
        Load trades from local SQLite database.

        Args:
            symbol: Trading pair (default: BTC/EUR)
            since: Start date for trades (default: all trades)
            limit: Maximum number of trades to return (default: all)
            db_path: Path to SQLite database (default: btc_eur_data.db in project root)

        Returns:
            List of trades in the same format as fetch_my_trades()
        """
        import os

        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'btc_eur_data.db')

        # Build SQL query
        query = "SELECT * FROM btc_eur_trades WHERE symbol = ?"
        params = [symbol]

        if since:
            since_timestamp_ms = int(since.timestamp() * 1000)
            query += " AND timestamp >= ?"
            params.append(since_timestamp_ms)

        query += " ORDER BY timestamp DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        # Execute query
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to ccxt trade format
            trades = []
            for row in rows:
                trade = {
                    'id': row['trade_id'],
                    'order': row['order_id'],
                    'symbol': row['symbol'],
                    'timestamp': row['timestamp'],
                    'datetime': row['datetime'],
                    'side': row['side'],
                    'price': float(row['price']),
                    'amount': float(row['amount']),
                    'cost': float(row['cost']),
                    'fee': {
                        'cost': float(row['fee_cost']),
                        'currency': row['fee_currency']
                    },
                    'maker': bool(row['is_maker'])
                }
                trades.append(trade)

            logger.info(f"Loaded {len(trades)} trades from database")
            return trades

    def sync_asset_history_to_database(
        self,
        since: Optional[datetime] = None,
        db_path: str = None
    ) -> Dict[str, Any]:
        """
        Synchronize asset history (deposits, withdrawals, converts) to database.

        Fetches and stores:
        - Deposits (fiat and crypto)
        - Withdrawals
        - Converts (Binance Convert trades)

        Args:
            since: Start date for sync (default: last sync or 1 year ago)
            db_path: Path to SQLite database

        Returns:
            Dictionary with sync statistics
        """
        import os

        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, 'btc_eur_data.db')

        logger.info("Starting asset history synchronization")
        logger.info(f"Database path: {db_path}")

        stats = {
            'deposits_synced': 0,
            'withdrawals_synced': 0,
            'converts_synced': 0,
            'total_synced': 0,
        }

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Get last sync timestamp
            cursor.execute("SELECT MAX(timestamp) FROM asset_transactions")
            result = cursor.fetchone()
            latest_timestamp_ms = result[0] if result[0] else None

            # Determine start date
            if since:
                since_timestamp_ms = int(since.timestamp() * 1000)
            elif latest_timestamp_ms:
                since_timestamp_ms = latest_timestamp_ms + 1
                logger.info(f"Incremental sync since {datetime.fromtimestamp(since_timestamp_ms / 1000)}")
            else:
                since = datetime.now() - timedelta(days=365)
                since_timestamp_ms = int(since.timestamp() * 1000)
                logger.info(f"Initial sync since {since}")

            # 1. Sync Deposits
            try:
                logger.info("Fetching deposit history...")
                deposits = self.exchange.fetch_deposits(since=since_timestamp_ms)
                logger.info(f"Fetched {len(deposits)} deposits")

                for deposit in deposits:
                    # Only include successful deposits
                    if deposit.get('status') != 'ok':
                        continue

                    try:
                        tx_id = f"deposit:{deposit['id']}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO asset_transactions (
                                transaction_id, transaction_type, timestamp, datetime,
                                status, currency, amount, fee, fee_currency,
                                network, address, tx_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            tx_id,
                            'deposit',
                            deposit['timestamp'],
                            datetime.fromtimestamp(deposit['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                            'success',
                            deposit['currency'],
                            float(deposit['amount']),
                            float(deposit.get('fee', {}).get('cost', 0)),
                            deposit.get('fee', {}).get('currency'),
                            deposit.get('network'),
                            deposit.get('address'),
                            deposit.get('txid')
                        ))

                        if cursor.rowcount > 0:
                            stats['deposits_synced'] += 1

                    except Exception as e:
                        logger.warning(f"Failed to insert deposit {deposit.get('id')}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error fetching deposits: {e}")

            # 2. Sync Withdrawals
            try:
                logger.info("Fetching withdrawal history...")
                withdrawals = self.exchange.fetch_withdrawals(since=since_timestamp_ms)
                logger.info(f"Fetched {len(withdrawals)} withdrawals")

                for withdrawal in withdrawals:
                    # Only include successful withdrawals
                    if withdrawal.get('status') != 'ok':
                        continue

                    try:
                        tx_id = f"withdrawal:{withdrawal['id']}"
                        cursor.execute("""
                            INSERT OR IGNORE INTO asset_transactions (
                                transaction_id, transaction_type, timestamp, datetime,
                                status, currency, amount, fee, fee_currency,
                                network, address, tx_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            tx_id,
                            'withdrawal',
                            withdrawal['timestamp'],
                            datetime.fromtimestamp(withdrawal['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                            'success',
                            withdrawal['currency'],
                            float(withdrawal['amount']),
                            float(withdrawal.get('fee', {}).get('cost', 0)),
                            withdrawal.get('fee', {}).get('currency'),
                            withdrawal.get('network'),
                            withdrawal.get('address'),
                            withdrawal.get('txid')
                        ))

                        if cursor.rowcount > 0:
                            stats['withdrawals_synced'] += 1

                    except Exception as e:
                        logger.warning(f"Failed to insert withdrawal {withdrawal.get('id')}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error fetching withdrawals: {e}")

            conn.commit()

            # Calculate total
            stats['total_synced'] = (
                stats['deposits_synced'] +
                stats['withdrawals_synced'] +
                stats['converts_synced']
            )

            # Get final counts
            cursor.execute("""
                SELECT transaction_type, COUNT(*)
                FROM asset_transactions
                GROUP BY transaction_type
            """)
            type_counts = dict(cursor.fetchall())

            logger.info(f"Asset history sync complete: {stats}")

            return {
                **stats,
                'total_in_db': {
                    'deposits': type_counts.get('deposit', 0),
                    'withdrawals': type_counts.get('withdrawal', 0),
                    'transfers': type_counts.get('transfer', 0),
                    'converts': type_counts.get('convert', 0),
                },
                'sync_timestamp': datetime.now().isoformat()
            }

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
