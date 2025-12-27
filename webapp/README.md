# Bitcoin Trading Web Application (BTC/EUR)

Django-basierte Web-Applikation zur interaktiven Visualisierung von Bitcoin-Kursdaten mit professionellen Trading-Charts.

## Features

- **Interaktive TradingView Charts**: Professionelle Candlestick-Charts mit nativem Zoom & Pan
- **Multi-Timeframe Support**: 15m, 1h, 4h, 1d Zeitrahmen
- **Technische Indikatoren**: RSI, SMA, EMA, Bollinger Bands
- **Live Price Display**: Aktueller Preis mit % Änderung
- **Auto-Refresh**: Optionale automatische Datenaktualisierung
- **REST API**: Vollständige REST API für Daten und Indikatoren
- **Dark Theme**: Professionelles Trading-Interface Design

## Technologie-Stack

- **Backend**: Django 5.0 + Django REST Framework
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Charts**: TradingView Lightweight Charts
- **Database**: Shared SQLite (btc_eur_data.db aus Hauptprojekt)
- **Indikatoren**: Python pandas/numpy

## Installation

### Voraussetzungen

- Python 3.8+
- Existierende Bitcoin-Datenbank (`btc_eur_data.db` im Parent-Verzeichnis)

### Schritt 1: Dependencies installieren

```bash
cd /Users/ikoerber/AIProjects/bitcoin/webapp
pip install -r requirements-webapp.txt
```

### Schritt 2: Django-Server starten

```bash
python manage.py runserver
```

### Schritt 3: Browser öffnen

```
http://localhost:8000/
```

## Verwendung

### Dashboard

1. **Timeframe wechseln**: Dropdown-Menü oben links
2. **Zoom**: Mausrad auf dem Chart
3. **Pan**: Klicken & Ziehen auf dem Chart
4. **Indikatoren**: Checkboxen zum Ein-/Ausschalten
5. **Refresh**: Button zum manuellen Aktualisieren
6. **Auto-Refresh**: Automatische Aktualisierung alle 60 Sekunden

### Verfügbare Indikatoren

- **RSI (14)**: Relative Strength Index
- **SMA (20)**: Simple Moving Average
- **EMA (20)**: Exponential Moving Average
- **Bollinger Bands**: Oberes, mittleres, unteres Band

## REST API Endpoints

### OHLCV Daten

```
GET /api/ohlcv/<timeframe>/?limit=500
```

**Parameter:**
- `timeframe`: 15m, 1h, 4h, 1d
- `limit`: Anzahl Candles (default: 500)
- `start`: Start-Datum (YYYY-MM-DD)
- `end`: End-Datum (YYYY-MM-DD)

**Response:**
```json
{
  "timeframe": "1h",
  "count": 500,
  "data": [
    {
      "time": 1703001600,
      "open": 91234.56,
      "high": 91500.00,
      "low": 91100.00,
      "close": 91450.00,
      "volume": 123.45
    },
    ...
  ]
}
```

### Latest Price

```
GET /api/latest-price/<timeframe>/
```

**Response:**
```json
{
  "timeframe": "1h",
  "timestamp": 1703001600,
  "datum": "2025-12-27 16:00:00",
  "close": 91450.00,
  "change_percent": 1.23
}
```

### Technical Indicators

```
GET /api/indicators/<timeframe>/?indicator=rsi&period=14
```

**Parameter:**
- `indicator`: rsi, sma, ema, bb
- `period`: Periode (default: 14 für RSI, 20 für andere)
- `limit`: Anzahl Datenpunkte (default: 500)

**Response (RSI/SMA/EMA):**
```json
{
  "timeframe": "1h",
  "indicator": "rsi",
  "period": 14,
  "count": 486,
  "data": [
    { "time": 1703001600, "value": 65.43 },
    ...
  ]
}
```

**Response (Bollinger Bands):**
```json
{
  "timeframe": "1h",
  "indicator": "bb",
  "period": 20,
  "count": 480,
  "data": [
    {
      "time": 1703001600,
      "upper": 92000.00,
      "middle": 91500.00,
      "lower": 91000.00
    },
    ...
  ]
}
```

### Database Summary

```
GET /api/summary/
```

**Response:**
```json
{
  "15m": {
    "table": "btc_eur_15m",
    "records": 1000,
    "earliest": "2025-11-16 00:00:00",
    "latest": "2025-12-27 16:00:00"
  },
  ...
}
```

## Projektstruktur

```
webapp/
├── manage.py                    # Django Management
├── requirements-webapp.txt      # Python Dependencies
├── bitcoin_webapp/              # Django Project Settings
│   ├── settings.py              # Configuration
│   ├── urls.py                  # URL Routing
│   ├── wsgi.py                  # WSGI Application
│   └── asgi.py                  # ASGI Application
└── charts/                      # Charts Django App
    ├── models.py                # Unmanaged Models (DB Access)
    ├── views.py                 # API Views + Dashboard
    ├── serializers.py           # DRF Serializers
    ├── indicators.py            # Technical Indicators
    ├── urls.py                  # App URL Routes
    ├── templates/charts/
    │   └── dashboard.html       # Main Dashboard
    └── static/charts/
        ├── css/style.css        # Dashboard Styling
        └── js/
            ├── api.js           # API Layer
            ├── indicators.js    # Indicator Manager
            └── chart.js         # Chart Controller
```

## Datenaktualisierung

Die Webapp nutzt die existierende Datenbank. Um neue Daten zu sammeln:

```bash
# In separatem Terminal, im Parent-Verzeichnis
cd /Users/ikoerber/AIProjects/bitcoin
python db_manager.py
```

Die Webapp zeigt automatisch die aktualisierten Daten nach dem nächsten Refresh.

## Entwicklung

### Django Admin (Optional)

```bash
python manage.py createsuperuser
python manage.py runserver
# http://localhost:8000/admin/
```

### Static Files sammeln (für Production)

```bash
python manage.py collectstatic
```

## Troubleshooting

### Problem: "Database not found"

**Lösung:** Stelle sicher, dass `btc_eur_data.db` im Parent-Verzeichnis existiert.

```bash
cd /Users/ikoerber/AIProjects/bitcoin
ls -la btc_eur_data.db
```

Falls nicht vorhanden, führe aus:

```bash
python db_manager.py
```

### Problem: "No module named 'rest_framework'"

**Lösung:** Dependencies installieren:

```bash
pip install -r requirements-webapp.txt
```

### Problem: Charts werden nicht angezeigt

**Lösung:**
1. Browser-Konsole öffnen (F12)
2. Prüfe auf JavaScript-Fehler
3. Stelle sicher, dass TradingView CDN erreichbar ist
4. Leere Browser-Cache (Strg+Shift+R)

### Problem: Keine Daten im Chart

**Lösung:**
1. Prüfe API-Endpoint: `http://localhost:8000/api/summary/`
2. Stelle sicher, dass Datenbank Einträge hat
3. Führe `python db_manager.py` aus, um Daten zu sammeln

## Performance

- **Chart Rendering**: ~100ms für 500 Candles
- **API Response**: <200ms typisch
- **Indikator-Berechnung**: <500ms für 1000 Datenpunkte
- **Memory**: ~100MB typisch

## Sicherheit

**Hinweis:** Diese Implementierung ist für **lokale Entwicklung** optimiert.

Für Production-Deployment:
- [ ] `DEBUG = False` in settings.py
- [ ] Starken `SECRET_KEY` generieren
- [ ] `ALLOWED_HOSTS` konfigurieren
- [ ] HTTPS aktivieren
- [ ] CSRF Protection aktivieren
- [ ] Authentication hinzufügen

## Browser-Kompatibilität

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Keyboard Shortcuts

- **+** / **-**: Zoom in/out
- **←** / **→**: Pan links/rechts
- **Esc**: Zoom zurücksetzen
- **F5**: Seite neu laden

## Weitere Ressourcen

- [TradingView Lightweight Charts Docs](https://tradingview.github.io/lightweight-charts/)
- [Django REST Framework Docs](https://www.django-rest-framework.org/)
- [Pandas Technical Analysis](https://pandas.pydata.org/)

## Version

**1.0.0** - Initial Release

## Lizenz

MIT License

---

**Entwickelt mit:** Django 5.0 + TradingView Lightweight Charts
**Datenquelle:** Binance (BTC/EUR)
