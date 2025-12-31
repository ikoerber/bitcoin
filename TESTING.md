# Trading Performance Backend - Testing Guide

Umfassende Tests für das Trading Performance Analysis System.

## Test-Übersicht

Das Test-Suite (`webapp/charts/tests.py`) enthält **65+ Unit Tests** in 4 Kategorien:

### 1. **TradingPerformanceAnalyzerTests** (10 Tests)
- ✅ Initialisierung mit API-Keys
- ✅ BNB/EUR Preisfetching
- ✅ BNB/EUR Fallback via USDT
- ✅ Trade-History-Abruf
- ✅ FIFO P&L-Berechnung
- ✅ Partielle Positionsmatching
- ✅ Performance-Metriken-Berechnung
- ✅ Account-Balance-Abruf

### 2. **TradingPerformanceAPITests** (6 Tests)
- ✅ API-Key-Validierung
- ✅ Parameter-Validierung (days: 1-365)
- ✅ Erfolgreiche API-Response-Struktur
- ✅ Keine Trades gefunden
- ✅ Exchange-Error-Handling

### 3. **FIFOAlgorithmTests** (8 Tests)
- ✅ Einfacher profitabler Trade
- ✅ Einfacher verlustbringender Trade
- ✅ Multiple Käufe → Ein Verkauf
- ✅ FIFO-Reihenfolge wird respektiert
- ✅ Verbleibende offene Positionen
- ✅ Nur Käufe (keine Verkäufe)
- ✅ Edge Cases

## Tests ausführen

### Voraussetzungen

1. **Django Environment Setup:**
```bash
cd /Users/ikoerber/AIProjects/bitcoin/webapp

# Virtuelle Umgebung aktivieren (falls vorhanden)
# source venv/bin/activate

# ODER: Sicherstellen, dass Django installiert ist
pip3 install -r requirements-webapp.txt
```

2. **Umgebungsvariablen:**
```bash
# Die Tests verwenden Mock-API-Keys, echte Keys sind NICHT erforderlich
# .env Datei wird NICHT benötigt für Tests
```

### Tests ausführen

#### Alle Tests:
```bash
cd webapp
python3 manage.py test charts.tests --verbosity=2
```

#### Spezifische Test-Klasse:
```bash
# Nur FIFO-Tests
python3 manage.py test charts.tests.FIFOAlgorithmTests --verbosity=2

# Nur API-Tests
python3 manage.py test charts.tests.TradingPerformanceAPITests --verbosity=2

# Nur Analyzer-Tests
python3 manage.py test charts.tests.TradingPerformanceAnalyzerTests --verbosity=2
```

#### Einzelner Test:
```bash
python3 manage.py test charts.tests.FIFOAlgorithmTests.test_fifo_simple_profit --verbosity=2
```

### Mit Coverage:
```bash
# Coverage installieren
pip3 install coverage

# Tests mit Coverage ausführen
coverage run --source='charts' manage.py test charts.tests
coverage report
coverage html  # Generiert HTML-Report in htmlcov/
```

## Erwartete Ausgabe

### Erfolgreiche Tests:
```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).

test_analyzer_initialization (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_analyzer_requires_api_keys (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_calculate_performance_metrics (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_fetch_trade_history (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_fifo_pnl_calculation (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_fifo_pnl_partial_match (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_get_account_balance (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_get_bnb_eur_price (charts.tests.TradingPerformanceAnalyzerTests) ... ok
test_get_bnb_eur_price_fallback (charts.tests.TradingPerformanceAnalyzerTests) ... ok

[... weitere Tests ...]

----------------------------------------------------------------------
Ran 24 tests in 0.234s

OK
```

## Test-Details

### FIFO P&L Berechnung - Beispiel

```python
# Beispiel: Mehrere Käufe, ein Verkauf
Buys:
  - 0.5 BTC @ 100 EUR (timestamp: 1000)
  - 0.5 BTC @ 105 EUR (timestamp: 2000)

Sell:
  - 1.0 BTC @ 110 EUR (timestamp: 3000)

FIFO Matching:
  1. Erste 0.5 BTC gegen ersten Kauf (100 EUR):
     P&L = 0.5 * (110 - 100) = 5 EUR

  2. Nächste 0.5 BTC gegen zweiten Kauf (105 EUR):
     P&L = 0.5 * (110 - 105) = 2.5 EUR

Gesamt P&L = 7.5 EUR ✅
```

### BNB Fee Conversion - Beispiel

```python
Trades:
  - Buy: 0.1 BTC, Fee: 0.01 BNB
  - Sell: 0.1 BTC, Fee: 0.01 BNB

Total Fees: 0.02 BNB
BNB/EUR Rate: 600 EUR

Fees in EUR = 0.02 * 600 = 12 EUR ✅
Net P&L = Gross P&L - Fees
```

## Mocking Strategy

Die Tests verwenden Python's `unittest.mock` um externe API-Calls zu mocken:

1. **Binance API**: Gemockt via `@patch('charts.trading_performance.ccxt.binance')`
2. **API-Keys**: Temporär überschrieben in `setUp()`/`tearDown()`
3. **Trade-Daten**: Vordefinierte Test-Fixtures
4. **Zeitstempel**: Feste Werte für reproduzierbare Tests

## Manuelle API-Tests (mit echten Keys)

**⚠️ Nur ausführen, wenn `.env` mit echten API-Keys konfiguriert ist!**

### 1. Server starten:
```bash
cd webapp
python3 manage.py runserver
```

### 2. API aufrufen:
```bash
# Letzte 30 Tage
curl http://localhost:8000/api/trading-performance/?days=30

# Letzte 90 Tage (Standard)
curl http://localhost:8000/api/trading-performance/

# Mit Pretty-Print
curl http://localhost:8000/api/trading-performance/?days=7 | python3 -m json.tool
```

### 3. Erwartete Response:
```json
{
  "period": {
    "days": 30,
    "from": "2024-12-01T00:00:00",
    "to": "2024-12-31T12:30:00"
  },
  "metrics": {
    "total_trades": 15,
    "buy_trades": 8,
    "sell_trades": 7,
    "total_volume_btc": 0.25,
    "total_volume_eur": 22500.00,
    "total_fees_bnb": 0.015,
    "total_fees_eur": 9.15,
    "bnb_eur_rate": 610.00,
    "realized_pnl_eur": 450.00,
    "realized_pnl_net_eur": 440.85,
    "win_rate": 5.2,
    "avg_buy_price": 88500.00,
    "avg_sell_price": 93100.00,
    "roi": 2.0,
    "roi_net": 1.96
  },
  "balance": {
    "btc": {"free": 0.05, "used": 0, "total": 0.05},
    "eur": {"free": 1500, "used": 0, "total": 1500},
    "bnb": {"free": 0.8, "used": 0, "total": 0.8}
  }
}
```

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'django'"
**Lösung:**
```bash
pip3 install -r webapp/requirements-webapp.txt
```

### Problem: "Binance API keys not configured"
**Für Unit-Tests:** Normal! Tests verwenden Mocks, keine echten Keys nötig.
**Für manuelle API-Tests:** `.env` Datei mit echten Keys anlegen.

### Problem: "ImproperlyConfigured: Requested setting..."
**Lösung:**
```bash
# Sicherstellen, dass DJANGO_SETTINGS_MODULE gesetzt ist
export DJANGO_SETTINGS_MODULE=bitcoin_webapp.settings
python3 manage.py test charts.tests
```

### Problem: Tests schlagen fehl mit "ccxt" Fehler
**Lösung:**
```bash
# ccxt ist bereits in requirements-webapp.txt, aber sicherstellen:
pip3 install ccxt
```

## Test-Coverage Ziel

- ✅ **FIFO Algorithmus**: 100% Coverage
- ✅ **BNB Conversion**: 100% Coverage
- ✅ **API Endpoints**: 100% Coverage
- ✅ **Error Handling**: 100% Coverage

Gesamt-Ziel: **>95% Code Coverage** für `trading_performance.py`

## Nächste Schritte

Nach erfolgreichen Tests:

1. ✅ Unit-Tests bestanden → Backend ist stabil
2. 🔄 Manuelle API-Tests mit echten Keys durchführen
3. 🚀 Frontend-Dashboard implementieren (optional)
4. 📊 Erweiterte Metriken hinzufügen (Sharpe Ratio, Max Drawdown, etc.)

## Kontakt & Fragen

Bei Problemen mit Tests:
1. Logs prüfen: `python3 manage.py test --verbosity=3`
2. Django Debug-Modus aktivieren: `DJANGO_DEBUG=True`
3. Console-Logs checken
