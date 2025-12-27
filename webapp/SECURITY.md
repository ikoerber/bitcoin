# Security Configuration Guide

## Quick Start (Development)

Für lokale Entwicklung funktioniert alles out-of-the-box. Die App zeigt Warnungen an, wenn unsichere Einstellungen verwendet werden.

```bash
cd webapp
python manage.py runserver
```

**Warnungen bei Start:**
```
WARNING: Using default SECRET_KEY. Set DJANGO_SECRET_KEY environment variable for production!
```

Dies ist für Development OK, aber **NIEMALS für Production!**

---

## Production Setup (WICHTIG!)

### 1. .env Datei erstellen

```bash
cp .env.example .env
```

### 2. Secret Key generieren

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Ausgabe (Beispiel):
```
django-insecure-xy7#$mf9!k2@pq8rnw3&vz4j6h5g
```

### 3. .env Datei editieren

```bash
# Beispiel .env für Production
DJANGO_SECRET_KEY=django-insecure-xy7#$mf9!k2@pq8rnw3&vz4j6h5g
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=bitcoinapp.example.com,www.bitcoinapp.example.com
CORS_ALLOWED_ORIGINS=https://bitcoinapp.example.com
BTC_DB_PATH=../btc_eur_data.db
LOG_LEVEL=INFO
```

### 4. Sicherstellen dass .env NICHT in Git committed wird

```bash
# .gitignore sollte enthalten:
.env
*.env
```

### 5. Server starten

```bash
python manage.py runserver  # Development
# ODER
gunicorn bitcoin_webapp.wsgi:application  # Production
```

---

## Umgebungsvariablen

### DJANGO_SECRET_KEY (KRITISCH)
- **Zweck:** Kryptografischer Schlüssel für Django
- **Development:** Default-Wert (mit Warnung)
- **Production:** **MUSS** gesetzt werden
- **Generierung:** `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- **Sicherheit:** Niemals in Git committen, niemals teilen

### DJANGO_DEBUG (KRITISCH)
- **Zweck:** Debug-Modus aktivieren/deaktivieren
- **Werte:** `True` oder `False`
- **Development:** `True` (zeigt Stack Traces)
- **Production:** **MUSS** `False` sein (zeigt keine sensiblen Daten)
- **Default:** `True`

### DJANGO_ALLOWED_HOSTS (WICHTIG)
- **Zweck:** Erlaubte Hostnamen für die Webapp
- **Format:** Komma-separiert
- **Development:** `localhost,127.0.0.1`
- **Production:** `yourdomain.com,www.yourdomain.com`
- **Default:** `localhost,127.0.0.1`

### CORS_ALLOWED_ORIGINS (WICHTIG)
- **Zweck:** Erlaubte Origins für CORS-Requests
- **Format:** Komma-separiert, mit Protokoll
- **Development:** `http://localhost:8000,http://127.0.0.1:8000`
- **Production:** `https://yourdomain.com`
- **Default:** `http://localhost:8000,http://127.0.0.1:8000`
- **Warnung:** NIEMALS `CORS_ALLOW_ALL=True` in Production!

### CORS_ALLOW_ALL (NUR DEVELOPMENT)
- **Zweck:** Erlaubt CORS von ALLEN Domains
- **Werte:** `True` oder `False`
- **Development:** Optional `True` für Testing
- **Production:** **NIEMALS** `True`
- **Default:** `False`
- **Zeigt Warnung** wenn auf `True` gesetzt

### BTC_DB_PATH (OPTIONAL)
- **Zweck:** Pfad zur SQLite-Datenbank
- **Default:** `../btc_eur_data.db` (relative zu webapp/)
- **Production:** Kann auf absoluten Pfad gesetzt werden

### LOG_LEVEL (OPTIONAL)
- **Zweck:** Logging-Level
- **Werte:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Development:** `DEBUG` oder `INFO`
- **Production:** `INFO` oder `WARNING`
- **Default:** `INFO`
- **Hinweis:** Aktuell noch nicht vollständig implementiert

---

## Sicherheits-Checkliste für Production

- [ ] `.env` Datei erstellt
- [ ] `DJANGO_SECRET_KEY` generiert und gesetzt
- [ ] `DJANGO_DEBUG=False` gesetzt
- [ ] `DJANGO_ALLOWED_HOSTS` auf echte Domain gesetzt
- [ ] `CORS_ALLOWED_ORIGINS` auf echte Domain gesetzt (mit HTTPS)
- [ ] `CORS_ALLOW_ALL=False` oder nicht gesetzt
- [ ] `.env` ist in `.gitignore`
- [ ] Server zeigt KEINE Warnungen beim Start
- [ ] HTTPS aktiviert (Let's Encrypt empfohlen)
- [ ] Firewall konfiguriert (nur Port 443/80 offen)

---

## Häufige Probleme

### "DisallowedHost" Error
**Symptom:** `DisallowedHost at / Invalid HTTP_HOST header: 'example.com'`

**Lösung:**
```bash
# In .env:
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
```

### CORS Error im Browser
**Symptom:** `Access to fetch at 'http://...' from origin '...' has been blocked by CORS policy`

**Lösung:**
```bash
# In .env:
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

### Secret Key Warnung
**Symptom:** `WARNING: Using default SECRET_KEY`

**Lösung:**
```bash
# Secret Key generieren
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# In .env:
DJANGO_SECRET_KEY=<generierter-key>
```

### CORS_ALLOW_ALL Warnung
**Symptom:** `WARNING: CORS_ALLOW_ALL_ORIGINS is True`

**Lösung:**
```bash
# In .env:
# Entferne CORS_ALLOW_ALL oder setze:
CORS_ALLOW_ALL=False
CORS_ALLOWED_ORIGINS=https://your-domain.com
```

---

## Testing

### Security Headers testen
```bash
# Check CORS
curl -H "Origin: http://evil-site.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS http://localhost:8000/api/ohlcv/1h/

# Sollte KEINEN Access-Control-Allow-Origin Header zurückgeben
```

### DEBUG=False testen
```bash
# Provoziere einen Fehler
curl http://localhost:8000/api/ohlcv/invalid_timeframe/

# Mit DEBUG=False: Generische Error-Page
# Mit DEBUG=True: Detaillierte Stack Trace
```

---

## Weitere Ressourcen

- [Django Security Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Let's Encrypt (HTTPS)](https://letsencrypt.org/)

---

**Zuletzt aktualisiert:** 2025-12-27
