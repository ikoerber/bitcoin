# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bitcoin Trading Data Application (BTC/EUR) - A comprehensive system for professional collection, storage, analysis, and visualization of Bitcoin market data against the Euro pair.

The system consists of two main components:
1. **CLI Tools** (Python scripts): Data collection, offline visualization, and technical analysis
2. **Web Application** (Django): Interactive web-based trading dashboard with real-time charts

Both components share a local SQLite database to store historical price data across four different timeframes, enabling fast analysis and backtesting of trading strategies without API limits or constant internet dependency. Data source is Binance exchange.

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

### CLI Tools
```bash
pip install ccxt pandas mplfinance numpy matplotlib
```

### Web Application (Additional)
```bash
cd webapp
pip install -r requirements-webapp.txt
# Includes: Django>=5.0.0, djangorestframework>=3.14.0, django-cors-headers>=4.3.0, python-dotenv>=1.0.0
```

## Core Components

### CLI Tools (Root Directory)
- `db_manager.py`: Data collection and database updates from Binance
- `visualizer.py`: Offline candlestick chart visualization (mplfinance)
- `strategy.py`: Technical analysis framework and pattern detection
- `btc_eur_data.db`: SQLite database (auto-created, shared by all components)

### Web Application (webapp/ Directory)
- `webapp/manage.py`: Django management script
- `webapp/bitcoin_webapp/`: Django project settings and configuration
- `webapp/charts/`: Django app for trading charts
  - `models.py`: Unmanaged Django models (connects to existing database)
  - `views.py`: REST API endpoints and dashboard view
  - `indicators.py`: Technical indicators (RSI, SMA, EMA, Bollinger Bands)
  - `trading_performance.py`: Trading performance analysis (Binance account data)
  - `tests.py`: Comprehensive unit tests (24+ tests for trading performance)
  - `serializers.py`: Django REST Framework serializers
  - `templates/charts/dashboard.html`: Interactive web dashboard
  - `static/charts/`: CSS and JavaScript files
    - `css/style.css`: Professional dark theme styling
    - `js/chart.js`: TradingView Lightweight Charts integration
    - `js/indicators.js`: Indicator management
    - `js/api.js`: API interaction layer

## Common Commands

### Data Management (CLI)
```bash
# Update database with latest market data
python db_manager.py

# Visualize data as candlestick charts (offline)
python visualizer.py

# Run technical analysis
python strategy.py
```

### Web Application
```bash
# Install webapp dependencies
cd webapp
pip install -r requirements-webapp.txt

# Start Django development server
python manage.py runserver

# Access web dashboard
# Browser: http://localhost:8000/
```

### REST API Endpoints (Webapp)
- `GET /` - Interactive trading dashboard
- `GET /api/ohlcv/<timeframe>/` - OHLCV candlestick data
- `GET /api/latest-price/<timeframe>/` - Latest price with % change
- `GET /api/indicators/<timeframe>/` - Technical indicators (RSI, SMA, EMA, Bollinger Bands)
- `GET /api/trend/<timeframe>/` - Trend analysis (Higher Highs/Higher Lows swing points)
- `GET /api/engulfing/<timeframe>/` - Bullish/Bearish engulfing candlestick patterns
- `GET /api/summary/` - Database summary for all timeframes
- `POST /api/update-database/` - Trigger database update from Binance (web-based)
- `GET /api/trading-performance/` - Personal trading performance analysis (requires API keys)

Parameters:
- `timeframe`: 15m, 1h, 4h, 1d
- `limit`: Number of candles (default: 500, max: 10000)
- `indicator`: rsi, sma, ema, bb
- `period`: Indicator period (14 for RSI, 20 for others)
- `days`: Trading performance lookback period (1-365, default: 90)

## Development Notes

### Data Collection Strategy
- **Initial Load**: Automatically fetches 5 years of historical data on first run
  - Downloads data in batches of 1000 candles per request
  - ~175 requests for 15m, ~44 for 1h, ~11 for 4h, ~2 for 1d
  - Estimated duration: 4-5 minutes for all timeframes
  - Progress logging after each batch
- **Incremental Updates**: Each timeframe checks latest timestamp and downloads only new candles
- **Duplicate Prevention**: Via timestamp primary keys
- **Rate Limiting**: 1 second delay between requests during initial load, 0.5s for updates
- **Safety Limits**: Maximum 100 requests per timeframe to prevent infinite loops

### Security & Configuration
- **API Safety**: All API interactions are read-only (no trading functionality)
- **Data Privacy**: Local SQLite storage, no API keys required for public market data
- **Binance API Integration**: Optional trading performance analysis with read-only API keys
  - API keys stored locally in `.env` file (never committed to Git)
  - Required permissions: "Enable Reading" only
  - **DO NOT enable**: Spot & Margin Trading, Futures, Withdrawals
  - Automatic `.env` loading via python-dotenv
  - Graceful degradation if API keys not configured
- **Production Hardening**: Environment variable configuration system implemented
  - `.env.example` template provided in `webapp/` directory
  - Configurable: SECRET_KEY, DEBUG, ALLOWED_HOSTS, CORS, BINANCE_API_KEY, BINANCE_API_SECRET
  - Security warnings for unsafe configurations (default SECRET_KEY, CORS_ALLOW_ALL)
  - See `webapp/SECURITY.md` for complete production deployment guide
- **Input Validation**: All user inputs validated (CLI tools and Django views)
- **DoS Protection**: Query limits enforced (MAX_QUERY_LIMIT=10000)
- **SQL Injection Prevention**: Whitelist validation for table names
- **Development Mode**: Default configuration ready for local development (DEBUG=True)

### Web Application Architecture
- **Backend**: Django 5.0 with Django REST Framework
- **Frontend**: TradingView Lightweight Charts v4.1.0 (JavaScript)
- **Database**: Unmanaged models (managed=False) - no migrations on existing database
- **Styling**: Professional dark theme optimized for trading
- **Features**:
  - Interactive candlestick charts with native zoom/pan
  - Real-time price display with percentage change
  - Toggle technical indicators (RSI, SMA, EMA, Bollinger Bands)
  - Candlestick pattern detection (Bullish/Bearish Engulfing)
  - Trend analysis with swing point detection (Higher Highs/Higher Lows)
  - Day analysis mode with auto-fit price scale (shows current + previous day)
  - Timeframe switching (15m, 1h, 4h, 1d)
  - Fixed candle limit (10,000 candles for maximum scrollable history)
  - Auto-refresh functionality (60-second intervals)
  - Web-based database update button (📥 Daten von Binance laden)
  - Trading performance analysis (optional, requires Binance API keys)
  - Responsive design for desktop and tablet
  - Comprehensive error handling with detailed console logging

### Technical Analysis Features (Implemented in Webapp)

#### Technical Indicators
- ✅ **RSI** (Relative Strength Index) - Period 14, division-by-zero safe
- ✅ **SMA** (Simple Moving Average) - Period 20
- ✅ **EMA** (Exponential Moving Average) - Period 20
- ✅ **Bollinger Bands** - Period 20, Std Dev 2.0

#### Candlestick Patterns
- ✅ **Bullish Engulfing** - Current candle completely engulfs previous down candle
- ✅ **Bearish Engulfing** - Current candle completely engulfs previous up candle
- Real-time pattern detection with visual markers on chart

#### Trend Analysis (Smart Money Concepts)
- ✅ **Higher Highs (HH)** - Uptrend swing point detection
- ✅ **Higher Lows (HL)** - Uptrend support level identification
- ✅ **Lower Highs (LH)** - Downtrend resistance level identification
- ✅ **Lower Lows (LL)** - Downtrend swing point detection
- Visual markers with color-coded labels (green for uptrend, red for downtrend)

#### Trading Performance Analysis
- ✅ **P&L Calculation** - FIFO (First-In-First-Out) algorithm for realized profit/loss
- ✅ **Fee Analysis** - BNB trading fees converted to EUR at current exchange rate
- ✅ **Win-Rate Calculation** - Percentage comparison of average buy vs sell prices
- ✅ **ROI Metrics** - Return on investment (gross and net after fees)
- ✅ **Account Balances** - Current BTC, EUR, and BNB holdings
- ✅ **Trade Statistics** - Total trades, buy/sell breakdown, volume analysis
- API endpoint: `GET /api/trading-performance/?days=90`
- Requires Binance read-only API keys in `.env` file

### Code Quality & Stability Improvements
- ✅ **Database Context Managers**: All SQLite operations use `with` statements for guaranteed cleanup
- ✅ **Input Validation**: Try-except blocks with fallback to safe defaults (CLI and Django)
- ✅ **Error Handling**: Comprehensive error handling with informative messages
- ✅ **Resource Management**: No database connection leaks, proper memory cleanup
- ✅ **Edge Case Handling**: Safe handling of empty data arrays and null values
- ✅ **Query Optimization**: ORDER BY -timestamp for fetching latest data first
- See `IMPROVEMENTS.md` for complete changelog and implementation details

### Future Development Areas
- ~~Technical indicators (RSI, MA, Bollinger Bands) implementation~~ ✅ Completed
- ~~Web-based database update functionality~~ ✅ Completed
- ~~Security hardening and production configuration~~ ✅ Completed
- ~~Candlestick pattern detection (Engulfing)~~ ✅ Completed
- ~~Trend analysis (Higher Highs/Higher Lows)~~ ✅ Completed
- ~~Trading performance analysis with Binance API~~ ✅ Completed
- ~~Unit tests for trading performance backend~~ ✅ Completed
- Frontend dashboard for trading performance visualization
- Alert system for price pattern notifications
- Backtesting framework for strategy validation
- Additional indicators (MACD, Stochastic, Fibonacci)
- More candlestick patterns (Doji, Hammer, Shooting Star, etc.)
- Export functionality (charts as PNG, data as CSV)
- WebSocket integration for real-time updates
- Multi-asset support (other crypto pairs)
- Unit tests for CLI tools

## Project Structure

```
bitcoin/
├── db_manager.py              # CLI: Data collection from Binance
├── visualizer.py              # CLI: Offline chart visualization (mplfinance)
├── strategy.py                # CLI: Technical analysis and pattern detection
├── requirements.txt           # CLI dependencies
├── btc_eur_data.db           # Shared SQLite database (auto-created)
├── bitcoin_data.log          # Application logs
├── CLAUDE.md                 # This file (AI assistant guide)
├── README.md                 # CLI tools documentation
├── IMPROVEMENTS.md           # Detailed changelog of code improvements
├── TESTING.md                # Testing guide for trading performance backend
└── webapp/                   # Django Web Application
    ├── manage.py             # Django management
    ├── requirements-webapp.txt   # Webapp dependencies (includes python-dotenv)
    ├── README.md             # Webapp documentation
    ├── QUICKSTART.md         # Quick start guide
    ├── SECURITY.md           # Production security configuration guide
    ├── .env.example          # Environment variables template (includes BINANCE_API_KEY)
    ├── .env                  # Local environment config (gitignored, user-created)
    ├── bitcoin_webapp/       # Django project settings
    │   ├── settings.py       # Configuration (env vars, security, dotenv loading)
    │   ├── urls.py           # Main URL routing
    │   └── wsgi.py/asgi.py   # Server configs
    └── charts/               # Django app
        ├── models.py         # Unmanaged models (4 timeframes)
        ├── views.py          # REST API + dashboard view + trading performance
        ├── indicators.py     # Technical indicators (RSI, SMA, EMA, BB)
        ├── trading_performance.py  # Trading performance analyzer (FIFO P&L, BNB fees)
        ├── tests.py          # Unit tests (24+ tests with mocks)
        ├── serializers.py    # DRF serializers
        ├── urls.py           # App URL routing
        ├── templates/charts/
        │   └── dashboard.html    # Main dashboard UI (indicators, patterns, trends)
        └── static/charts/
            ├── css/style.css     # Dark theme styling
            └── js/
                ├── chart.js      # TradingView Lightweight Charts + patterns + trends
                ├── indicators.js # Indicator management
                └── api.js        # API interaction layer
```

## Quick Start

### Option 1: CLI Tools Only
```bash
# Install dependencies
pip install -r requirements.txt

# Collect data
python db_manager.py

# Visualize (offline charts)
python visualizer.py

# Analyze
python strategy.py
```

### Option 2: Web Application
```bash
# 1. Install CLI dependencies and collect data
pip install -r requirements.txt
python db_manager.py

# 2. Install webapp dependencies
cd webapp
pip install -r requirements-webapp.txt

# 3. Start Django server
python manage.py runserver

# 4. Open browser
# http://localhost:8000/
```

## Tips for Working with This Project

- **Data First**: Always run `python db_manager.py` before using visualizer or webapp
- **Shared Database**: Both CLI tools and webapp use the same `btc_eur_data.db`
- **No Migrations**: Webapp uses unmanaged models - never run Django migrations
- **Development Mode**: Default configuration ready for local development (DEBUG=True)
- **Production Deployment**: See `webapp/SECURITY.md` for complete security checklist
- **Code Quality**: All improvements documented in `IMPROVEMENTS.md`
- **Environment Configuration**:
  - Copy `webapp/.env.example` to `webapp/.env` for custom settings
  - Add Binance API keys to `.env` for trading performance features
  - `.env` is gitignored and never committed to repository
- **Testing**:
  - See `TESTING.md` for complete testing guide
  - Run tests: `cd webapp && python3 manage.py test charts.tests`
  - 24+ unit tests with full mocking (no real API calls needed)
- **Documentation**:
  - `webapp/README.md` - Detailed webapp documentation
  - `webapp/QUICKSTART.md` - Quick start guide
  - `webapp/SECURITY.md` - Production security guide
  - `TESTING.md` - Testing guide for trading performance
  - `IMPROVEMENTS.md` - Complete changelog with examples

## Trading Performance Analysis

### Setup
1. Get Binance read-only API keys: https://www.binance.com/en/my/settings/api-management
2. Enable **only** "Enable Reading" permission
3. **DO NOT enable**: Spot & Margin Trading, Futures, Withdrawals
4. Add keys to `webapp/.env`:
   ```
   BINANCE_API_KEY=your-api-key-here
   BINANCE_API_SECRET=your-api-secret-here
   ```
5. Restart Django server

### Usage
```bash
# Via curl
curl http://localhost:8000/api/trading-performance/?days=30

# Or access via browser/JavaScript fetch
fetch('/api/trading-performance/?days=90')
```

### Metrics Provided
- **Realized P&L**: FIFO-matched profit/loss in EUR
- **Net P&L**: P&L minus trading fees (BNB converted to EUR)
- **Win-Rate**: Average sell price vs average buy price percentage
- **ROI**: Return on investment (gross and net)
- **Trade Statistics**: Total trades, buy/sell counts, volume
- **Account Balances**: Current BTC, EUR, BNB holdings
- **Fee Analysis**: Total BNB fees converted to EUR at current rate
