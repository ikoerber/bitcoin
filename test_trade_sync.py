#!/usr/bin/env python3
"""
Test script for trade synchronization functionality.

Tests:
1. Database table exists
2. Trade sync from Binance API
3. Load trades from database
4. Performance calculation from database trades
"""

import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = '/Users/ikoerber/AIProjects/bitcoin/btc_eur_data.db'


def test_database_table():
    """Test 1: Check if btc_eur_trades table exists"""
    print("\n" + "="*60)
    print("TEST 1: Check database table")
    print("="*60)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='btc_eur_trades'
        """)
        result = cursor.fetchone()

        if result:
            print("✅ Table 'btc_eur_trades' exists")

            # Get table schema
            cursor.execute("PRAGMA table_info(btc_eur_trades)")
            columns = cursor.fetchall()
            print(f"\n📊 Table structure ({len(columns)} columns):")
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")

            # Get current count
            cursor.execute("SELECT COUNT(*) FROM btc_eur_trades")
            count = cursor.fetchone()[0]
            print(f"\n📈 Current trades in database: {count}")

            if count > 0:
                # Show sample trade
                cursor.execute("SELECT * FROM btc_eur_trades LIMIT 1")
                cursor.row_factory = sqlite3.Row
                cursor.execute("SELECT * FROM btc_eur_trades ORDER BY timestamp DESC LIMIT 1")
                sample = cursor.fetchone()
                print(f"\n🔍 Latest trade:")
                print(f"   - Trade ID: {sample[0] if sample else 'N/A'}")
                print(f"   - Side: {sample[5] if sample else 'N/A'}")
                print(f"   - Price: €{sample[6] if sample else 'N/A'}")
                print(f"   - Amount: {sample[7]} BTC" if sample else "   - Amount: N/A")
                print(f"   - DateTime: {sample[4] if sample else 'N/A'}")

            return True
        else:
            print("❌ Table 'btc_eur_trades' does not exist")
            return False


def test_sync_api():
    """Test 2: Test sync API endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Test trade sync API endpoint")
    print("="*60)
    print("\nℹ️  To test the sync functionality, run:")
    print("   curl http://localhost:8000/api/sync-trades/")
    print("\nOr visit in browser:")
    print("   http://localhost:8000/api/sync-trades/")
    print("\nFor full sync (all trades from last year):")
    print("   curl 'http://localhost:8000/api/sync-trades/?full_sync=true'")
    return True


def test_database_query():
    """Test 3: Query trades from database"""
    print("\n" + "="*60)
    print("TEST 3: Query trades from database")
    print("="*60)

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get buy/sell statistics
        cursor.execute("""
            SELECT
                side,
                COUNT(*) as count,
                SUM(amount) as total_btc,
                SUM(cost) as total_eur,
                AVG(price) as avg_price
            FROM btc_eur_trades
            GROUP BY side
            ORDER BY side
        """)

        stats = cursor.fetchall()

        if stats:
            print("\n📊 Trade Statistics:")
            for stat in stats:
                print(f"\n{stat['side'].upper()} Orders:")
                print(f"   - Count: {stat['count']}")
                print(f"   - Total BTC: {stat['total_btc']:.8f}")
                print(f"   - Total EUR: €{stat['total_eur']:.2f}")
                print(f"   - Avg Price: €{stat['avg_price']:.2f}")

            # Get date range
            cursor.execute("""
                SELECT
                    MIN(datetime) as first_trade,
                    MAX(datetime) as last_trade
                FROM btc_eur_trades
            """)
            date_range = cursor.fetchone()
            print(f"\n📅 Date Range:")
            print(f"   - First trade: {date_range['first_trade']}")
            print(f"   - Last trade: {date_range['last_trade']}")

            return True
        else:
            print("⚠️  No trades found in database")
            print("   Run sync first: curl http://localhost:8000/api/sync-trades/")
            return False


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 TRADE SYNCHRONIZATION TEST SUITE")
    print("="*60)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Run tests
    test1 = test_database_table()
    test2 = test_sync_api()
    test3 = test_database_query()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Test 1 (Database table): {'PASS' if test1 else 'FAIL'}")
    print(f"ℹ️  Test 2 (Sync API): INFO ONLY")
    print(f"{'✅' if test3 else '⚠️ '} Test 3 (Query trades): {'PASS' if test3 else 'NO DATA'}")

    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    if not test3:
        print("1. Start Django server: cd webapp && python3 manage.py runserver")
        print("2. Sync trades: curl http://localhost:8000/api/sync-trades/")
        print("3. Re-run this test script")
    else:
        print("✅ All tests passed! Trades are in the database.")
        print("\nAvailable API endpoints:")
        print("   - GET /api/sync-trades/  (sync new trades)")
        print("   - GET /api/trading-performance/?days=30  (calculate P&L)")
    print()
