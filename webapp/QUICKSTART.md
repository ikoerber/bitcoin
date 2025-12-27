# Bitcoin Trading Webapp - Schnellstart

## 🚀 In 3 Schritten zur laufenden Webapp

### Schritt 1: Dependencies installieren

```bash
cd /Users/ikoerber/AIProjects/bitcoin/webapp
pip install -r requirements-webapp.txt
```

**Installiert:**
- Django 5.0+
- Django REST Framework
- pandas, numpy
- django-cors-headers

### Schritt 2: Sicherstellen, dass Daten vorhanden sind

```bash
# Im Parent-Verzeichnis
cd /Users/ikoerber/AIProjects/bitcoin
python db_manager.py
```

**Dies sammelt aktuelle BTC/EUR-Daten von Binance.**

### Schritt 3: Django-Server starten

```bash
cd /Users/ikoerber/AIProjects/bitcoin/webapp
python manage.py runserver
```

**Output sollte sein:**
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Schritt 4: Browser öffnen

Gehe zu: **http://localhost:8000/**

---

## ✅ Checkliste - Was du sehen solltest

1. **Dashboard lädt** - Header mit "BTC/EUR Trading Dashboard"
2. **Aktueller Preis** wird angezeigt (oben rechts)
3. **Candlestick Chart** mit grünen/roten Kerzen
4. **Volume Chart** darunter
5. **Controls** - Timeframe-Dropdown (15m, 1h, 4h, 1d)
6. **Indikator-Checkboxen** - RSI, SMA, EMA, Bollinger Bands

---

## 🎯 Erste Schritte

### Timeframe wechseln
- Klicke auf Dropdown oben: **1 Stunde** → wähle **4 Stunden**
- Chart lädt automatisch neu

### Zoom & Pan testen
- **Zoom**: Mausrad auf dem Chart
- **Pan**: Linke Maustaste gedrückt halten und ziehen

### Indikatoren aktivieren
- Klicke Checkbox **RSI (14)** → Orange Linie erscheint
- Klicke Checkbox **Bollinger Bands** → Drei blaue Linien erscheinen

### Auto-Refresh aktivieren
- Klicke Button **Auto-Refresh: AUS**
- Button wird grün: **Auto-Refresh: AN**
- Daten aktualisieren sich nun alle 60 Sekunden

---

## 🔍 API testen (optional)

### Browser API-Test

Öffne diese URLs in deinem Browser:

1. **OHLCV Daten (1h, 100 Candles):**
   ```
   http://localhost:8000/api/ohlcv/1h/?limit=100
   ```

2. **Aktueller Preis (1h):**
   ```
   http://localhost:8000/api/latest-price/1h/
   ```

3. **RSI Indikator (1h, Periode 14):**
   ```
   http://localhost:8000/api/indicators/1h/?indicator=rsi&period=14
   ```

4. **Datenbank-Zusammenfassung:**
   ```
   http://localhost:8000/api/summary/
   ```

### cURL API-Test

```bash
# OHLCV Daten
curl http://localhost:8000/api/ohlcv/1h/?limit=10

# Latest Price
curl http://localhost:8000/api/latest-price/1h/

# RSI Indikator
curl "http://localhost:8000/api/indicators/1h/?indicator=rsi&period=14"

# Bollinger Bands
curl "http://localhost:8000/api/indicators/4h/?indicator=bb&period=20"
```

---

## 🛠️ Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'rest_framework'"

**Lösung:**
```bash
pip install djangorestframework
```

### Problem: "No such table: btc_eur_1h"

**Lösung:** Datenbank fehlt oder ist leer.
```bash
cd /Users/ikoerber/AIProjects/bitcoin
python db_manager.py
```

### Problem: Chart bleibt auf "Lädt..."

**Lösung:**
1. Browser-Konsole öffnen (F12)
2. Prüfe auf JavaScript-Fehler
3. Prüfe API: http://localhost:8000/api/summary/
4. Falls API leer: `python db_manager.py` ausführen

### Problem: "DisallowedHost"

**Lösung:** In `bitcoin_webapp/settings.py`:
```python
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']
```

### Problem: Static Files nicht gefunden

**Lösung:**
```bash
python manage.py collectstatic --noinput
```

---

## 📊 Daten aktualisieren

**Manuelle Aktualisierung:**
```bash
cd /Users/ikoerber/AIProjects/bitcoin
python db_manager.py
```

**In Webapp:** Klicke "Aktualisieren"-Button oder aktiviere Auto-Refresh

---

## 🎓 Erweiterte Features testen

### 1. Mehrere Indikatoren gleichzeitig

- Aktiviere **RSI** + **SMA** + **Bollinger Bands**
- Beobachte Überschneidungen und Signale

### 2. Verschiedene Timeframes vergleichen

- Öffne Dashboard in **2 Browser-Tabs**
- Tab 1: 15m Timeframe
- Tab 2: 4h Timeframe
- Vergleiche Trends

### 3. Historical Data Zoom

- Zoome weit heraus (Mausrad)
- Siehe gesamten Datenverlauf
- Zoome auf interessante Bereiche

---

## 🔄 Workflow-Beispiel

**Tägliche Bitcoin-Analyse:**

1. **Morgens:**
   ```bash
   cd /Users/ikoerber/AIProjects/bitcoin
   python db_manager.py  # Neue Daten holen
   cd webapp
   python manage.py runserver
   ```

2. **Im Browser:**
   - http://localhost:8000/
   - Timeframe: **1d** (Tageschart)
   - Aktiviere: **SMA**, **Bollinger Bands**
   - Analysiere Trend

3. **Intraday-Trading:**
   - Wechsel zu **15m** oder **1h**
   - Aktiviere **RSI** für Überkauft/Überverkauft
   - Auto-Refresh: **AN**

---

## 📝 Nächste Schritte

Nach erfolgreichem Start kannst du:

1. **Weitere Indikatoren hinzufügen** (MACD, Stochastic)
2. **Pattern Recognition integrieren** (aus strategy.py)
3. **Alerts implementieren** (Email bei RSI > 70)
4. **Export-Funktion** (Charts als PNG, Daten als CSV)

---

## ✨ Quick Reference

| Aktion | Shortcut/Methode |
|--------|------------------|
| Zoom In | Mausrad nach oben |
| Zoom Out | Mausrad nach unten |
| Pan | Linke Maustaste + Ziehen |
| Reset Zoom | Doppelklick auf Chart |
| Timeframe wechseln | Dropdown oben |
| Indikator an/aus | Checkbox |
| Refresh | Button oder F5 |
| Auto-Refresh | Button (60s Intervall) |

---

**Viel Erfolg mit deiner Bitcoin Trading Webapp!** 🚀📈
