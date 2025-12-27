# Bitcoin Trading Data Application (BTC/EUR)

A professional Python application for collecting, storing, and analyzing Bitcoin market data against the Euro pair from Binance exchange.

## Features

- **Multi-Timeframe Data Collection**: Automatic collection of OHLCV data across 4 timeframes (15m, 1h, 4h, 1d)
- **Local SQLite Database**: Fast, offline-capable storage without API dependencies
- **Professional Visualization**: Candlestick charts with volume analysis using mplfinance
- **Technical Analysis Framework**: Statistical analysis and pattern detection foundation
- **Incremental Updates**: Smart data collection that only fetches new candles
- **Comprehensive Logging**: Detailed logging to both console and file

## System Architecture

### Multi-Timeframe System

| Timeframe | Database Table | Use Case |
|-----------|----------------|----------|
| 15m | btc_eur_15m | Day trading, precise entries |
| 1h | btc_eur_1h | Intraday trends, short-term patterns |
| 4h | btc_eur_4h | Swing trading, medium-term trends |
| 1d | btc_eur_1d | Long-term bias, investment decisions |

### Data Source
- **Exchange**: Binance (public API, no authentication required)
- **Market**: BTC/EUR (Bitcoin/Euro spot pair)
- **Data Type**: OHLCV (Open, High, Low, Close, Volume)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. Clone or download this repository:
```bash
cd bitcoin
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

That's it! No API keys or additional configuration needed.

## Usage

### 1. Collect Market Data

Run the data manager to collect and store BTC/EUR market data:

```bash
python db_manager.py
```

This will:
- Connect to Binance exchange
- Create the SQLite database (btc_eur_data.db) if it doesn't exist
- Download historical data for all timeframes
- Perform incremental updates on subsequent runs

**First run**: Downloads ~1000 candles per timeframe (initial historical data)
**Subsequent runs**: Only fetches new candles since last update

### 2. Visualize Data

Launch the interactive visualizer:

```bash
python visualizer.py
```

Available visualization modes:
1. **Single timeframe** - Interactive chart display
2. **Generate all charts** - Save charts to files (batch mode)
3. **Display all charts** - Show all timeframes interactively
4. **Quick view** - 1h timeframe, last 7 days (default)

Example workflows:
```bash
# Quick check of recent 1h price action
python visualizer.py
# (Press Enter to use default quick view)

# Interactive single timeframe
python visualizer.py
# Select option 1, choose timeframe (e.g., "4h"), specify days
```

### 3. Technical Analysis

Run the strategy analyzer for statistical insights:

```bash
python strategy.py
```

Analysis modes:
1. **Market overview** - Current market state with recent trends
2. **Statistical analysis** - Comprehensive price and volume statistics
3. **Multi-timeframe analysis** - Compare all timeframes simultaneously
4. **Custom analysis** - Load specific data for detailed inspection

Example:
```bash
python strategy.py
# Select option 1 for quick market overview
# Or option 3 for comprehensive multi-timeframe analysis
```

## Project Structure

```
bitcoin/
├── db_manager.py         # Data collection and database management
├── visualizer.py         # Candlestick chart visualization
├── strategy.py           # Technical analysis and statistics
├── requirements.txt      # Python dependencies
├── btc_eur_data.db      # SQLite database (auto-created)
├── bitcoin_data.log     # Application log file (auto-created)
├── CLAUDE.md            # Development guidelines
└── README.md            # This file
```

## Database Schema

Each timeframe table (`btc_eur_15m`, `btc_eur_1h`, `btc_eur_4h`, `btc_eur_1d`) contains:

| Column | Type | Description |
|--------|------|-------------|
| timestamp | INTEGER PRIMARY KEY | Unix timestamp in milliseconds |
| open | REAL | Opening price (EUR) |
| high | REAL | Highest price in period (EUR) |
| low | REAL | Lowest price in period (EUR) |
| close | REAL | Closing price (EUR) |
| volume | REAL | Trading volume (BTC) |
| datum | TEXT | Human-readable datetime |

## Data Collection Strategy

### Incremental Updates
- Each run checks the latest timestamp in the database
- Only new candles are downloaded (minimal API usage)
- Duplicate prevention via primary key constraints

### Rate Limiting
- Built-in rate limit compliance with Binance API
- Small delays between requests to prevent hitting limits
- Safe for frequent updates

### Initial Load
- First run collects ~1000 recent candles per timeframe
- Provides sufficient historical data for immediate analysis
- Can be adjusted via `initial_limit` parameter

## Example Workflow

Complete workflow from scratch:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Collect initial data
python db_manager.py
# Wait for data collection to complete (~30-60 seconds)

# 3. View latest market state
python strategy.py
# Select option 1 for market overview

# 4. Visualize 4-hour chart for last 30 days
python visualizer.py
# Select option 1, enter "4h", enter "30"

# 5. Generate analysis reports for all timeframes
python strategy.py
# Select option 3 for multi-timeframe analysis
```

## Logging

All modules write detailed logs to:
- **Console**: INFO level and above
- **File**: `bitcoin_data.log` (all levels)

Log entries include:
- Timestamp
- Module name
- Log level
- Detailed message

## Security & Privacy

- **Read-only operations**: No trading functionality, only data retrieval
- **No authentication required**: Uses public Binance market data
- **Local storage**: All data stored locally in SQLite database
- **No external dependencies**: Data analysis works offline after collection

## Future Development

Planned enhancements (see `strategy.py` framework):

### Technical Indicators
- RSI (Relative Strength Index)
- Moving Averages (SMA, EMA)
- Bollinger Bands
- MACD (Moving Average Convergence Divergence)

### Advanced Features
- Alert system for price patterns
- Backtesting framework for strategy validation
- Multi-asset support
- Real-time data streaming

## Troubleshooting

### "Database not found" Error
**Cause**: Trying to run visualizer/strategy before collecting data
**Solution**: Run `python db_manager.py` first

### "No data available" Warning
**Cause**: Table is empty for selected timeframe
**Solution**: Run `python db_manager.py` to collect data

### "Network error" or "Exchange error"
**Cause**: Binance API connectivity issues
**Solution**: Check internet connection, wait a moment, try again

### Empty charts or old data
**Cause**: Database hasn't been updated recently
**Solution**: Run `python db_manager.py` to fetch latest candles

## Technical Requirements

- **Python**: 3.8+
- **Internet**: Required for data collection only
- **Disk Space**: ~10-50 MB for database (grows with historical data)
- **RAM**: Minimal (< 100 MB typical usage)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| ccxt | ≥4.0.0 | Binance exchange connectivity |
| pandas | ≥2.0.0 | Data manipulation and analysis |
| mplfinance | ≥0.12.10b0 | Candlestick chart generation |
| matplotlib | ≥3.7.0 | Chart rendering backend |
| numpy | ≥1.24.0 | Numerical computations |

## License

MIT License - See project documentation for details.

## Support

For issues, questions, or contributions:
1. Check the logs in `bitcoin_data.log`
2. Review this README and CLAUDE.md
3. Ensure all dependencies are correctly installed

## Performance Notes

- **Data collection**: 30-60 seconds for initial load of all timeframes
- **Chart generation**: 1-2 seconds per chart
- **Database queries**: < 100ms for typical analysis
- **Memory usage**: Efficient, handles years of data without issues

## Best Practices

1. **Regular updates**: Run `db_manager.py` daily or before analysis sessions
2. **Backup database**: Periodically copy `btc_eur_data.db` to preserve historical data
3. **Monitor logs**: Check `bitcoin_data.log` for any issues
4. **Respect rate limits**: Don't run data collection more than once per minute
5. **Start with quick views**: Use default options to verify setup before custom analysis

---

**Version**: 1.0
**Last Updated**: 2025-12-27
**Status**: Production Ready
