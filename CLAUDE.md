# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bitcoin Trading Data Application (BTC/EUR) - A Python application for professional collection, storage, and analysis of Bitcoin market data against the Euro pair.

The system uses a local SQLite database to store historical price data across four different timeframes, enabling fast analysis and backtesting of trading strategies without API limits or constant internet dependency. Data source is Binance exchange.

## Architecture

### Data Source & Market
- Exchange: Binance (via ccxt API)
- Market: BTC/EUR (Bitcoin against Euro)
- Data Type: OHLCV (Open, High, Low, Close, Volume)

### Multi-Timeframe System
The system manages four parallel data streams for different trading styles:

| Timeframe | Database Table | Use Case |
|-----------|----------------|----------|
| 15m | btc_eur_15m | Day trading, precise entries |
| 1h | btc_eur_1h | Intraday trends, short-term patterns |
| 4h | btc_eur_4h | Swing trading, medium-term trends |
| 1d | btc_eur_1d | Long-term bias, investment decisions |

### Database Schema (SQLite)
Each timeframe table contains:
- `timestamp` (INTEGER, Primary Key): Unix timestamp
- `open`, `high`, `low`, `close`, `volume` (REAL): OHLCV data
- `datum` (TEXT): Human-readable datetime

## Dependencies
```bash
pip install ccxt pandas mplfinance
```

## Core Components
- `db_manager.py`: Data collection and database updates from Binance
- `visualizer.py`: Candlestick chart visualization with selectable timeframes  
- `strategy.py`: Technical indicator calculations and signal generation
- `btc_eur_data.db`: SQLite database (auto-created)
## Common Commands

### Data Management
```bash
# Update database with latest market data
python db_manager.py

# Visualize data as candlestick charts
python visualizer.py
```

## Development Notes

### Data Collection Strategy
- Incremental updates: Each timeframe checks latest timestamp and downloads only new candles
- Duplicate prevention via timestamp primary keys
- Minimal API calls to respect Binance rate limits

### Security Considerations
- All API interactions are read-only (no trading functionality)
- No API keys required for public market data
- Local SQLite storage for data privacy

### Future Development Areas
- Technical indicators (RSI, MA, Bollinger Bands) implementation
- Alert system for price pattern notifications
- Backtesting framework for strategy validation
