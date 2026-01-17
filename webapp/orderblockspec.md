Spezifikation

Unten ist eine implementierbare Spezifikation für eure Django/SQLite-App, die (1) Binance Orderbuch via WebSocket sauber reinholt (inkl. lokalem L2-Buch) und (2) Order-Blocks (1h) nach dem ATR/BOS-Algorithmus berechnet – plus REST-Overlays für TradingView Lightweight Charts.

Ich schreibe das so, dass ein Dev-Team das ohne Interpretationsspielraum umsetzen kann. Wo ihr noch keine Entscheidung habt, setze ich Defaults als Config, damit ihr nicht blockiert seid.

⸻

0) Executive Summary

Zielbild
	•	Orderbuch (L2) wird per Binance WebSocket Diff Depth gepflegt, lokal gemanaged (Snapshot+Diff).
	•	Daraus werden Liquidity Walls und Cluster-Zonen (Support/Resistance als Liquiditätsbänder) berechnet.
	•	Parallel werden aus euren 1h OHLCV im SQLite Order Blocks (SMC-pragmatisch) berechnet.
	•	Beide Artefakte werden über Django REST als Overlays an Lightweight Charts geliefert (Boxes/Zones).
	•	Rolling Window: Orderbook-Rohdaten bleiben im RAM, in SQLite landen nur abgeleitete Features/Zonen (klein, performant).

Wahrheit in einem Satz
Orderbook ist Mikrostruktur, Orderblocks sind Chartstruktur. Ihr kombiniert beides: OB = „wo“, Orderbook-Zonen = „ob & wie“.

⸻

1) Nicht-Ziele (damit es nicht ausufert)
	•	Kein Auto-Trading / Order Placement.
	•	Kein Futures.
	•	Kein Multi-Symbol.
	•	Kein „Tick-genaues“ Persistieren des kompletten Orderbooks in SQLite (das killt euch bei 100ms Updates).

⸻

2) Externe Schnittstellen (Binance)

2.1 WebSocket Streams

Wir nutzen Diff. Depth Stream für lokales Orderbuch-Management:
<symbol>@depth oder <symbol>@depth@100ms  

Für BTC/EUR auf Binance Spot ist das Symbol i.d.R. btceur → Stream z.B.:
wss://stream.binance.com:9443/ws/btceur@depth@100ms

Update-Geschwindigkeit laut Doku: 1000ms oder 100ms  

2.2 REST Snapshot (Initialisierung / Resync)

Für korrektes lokales Buch braucht ihr initial Depth Snapshot via REST:
GET /api/v3/depth?symbol=BTCEUR&limit=5000  

Die Binance-Doku beschreibt den korrekten Ablauf (Buffering, lastUpdateId, Sequenzprüfung, Restart bei Gaps). Das ist nicht optional, das ist Pflicht, sonst ist euer Buch irgendwann Müll.  

2.3 Rate Limits (harte Realität)

Binance hat Request-Weight Limits (Beispiel: 6.000 request weight / Minute) – das kann sich ändern, steht auch in exchangeInfo.  
Konsequenz: WebSocket ist der richtige Weg. REST wird nur für Snapshot/Resync genutzt.

⸻

3) Architektur

3.1 Komponenten
	1.	Orderbook Streamer (separater Prozess)
	•	Django Management Command: python manage.py orderbook_stream
	•	Hält OrderbookState im RAM (bids/asks maps + updateId)
	•	Liest Diff-Events via WebSocket, pflegt lokales Buch
	•	Publiziert komprimierte Artefakte (Top-of-Book, Zonen, Metriken) periodisch in SQLite
	2.	Orderbook Analytics Engine (im Streamer)
	•	Wall-Detection + Cluster-Zonen
	•	Persistenz-Tracking (Zone muss „stehen bleiben“, nicht 2 Sekunden flackern)
	3.	Order Block Engine (Django Job)
	•	Läuft in eurer bestehenden APScheduler-Logik oder als separater CLI-Run
	•	Rechnet 1h-Orderblocks aus DB
	•	Schreibt Ergebnisse in SQLite
	4.	Django REST API
	•	Liefert Overlays (Orderblocks + Liquidity Zones) im Format für Lightweight Charts
	5.	Frontend (Lightweight Charts v4.1.0)
	•	Pollt Overlays (z.B. alle 2–5s)
	•	Rendert Rechtecke/Boxen für OBs und Zonen

3.2 Warum separater Prozess?

Django runserver/WSGI ist nicht euer Async-Worker. Ihr wollt keine WebSocket-Loop im Request-Prozess. Das endet in Zombie-Threads.
Der Streamer läuft als Dienst (lokal: separate Konsole; prod: systemd/supervisor/Gunicorn daneben).

⸻

4) Datenmodelle (SQLite)

4.1 Neue Tabellen (minimal, rolling-window-tauglich)

orderbook_metrics
	•	ts_ms (INTEGER, PK oder Index) – Event-/Publizierzeit
	•	symbol (TEXT) – „BTC/EUR“
	•	best_bid (REAL)
	•	best_ask (REAL)
	•	spread (REAL)
	•	mid (REAL)
	•	imbalance_topn (REAL) – z.B. (sumBidTopN - sumAskTopN) / (sumBidTopN + sumAskTopN)
	•	update_id (INTEGER)

Retention: z.B. 24h (Rolling Window per Delete Job).

orderbook_zones_current

Nur „current state“, damit UI schnell ist:
	•	id (TEXT, PK) – deterministisch (symbol+side+price_low+price_high)
	•	ts_ms (INTEGER) – last update
	•	symbol (TEXT)
	•	side (TEXT) – bid/ask
	•	price_low (REAL)
	•	price_high (REAL)
	•	notional (REAL) – Sum(qty*price) oder Sum(qty)
	•	strength (REAL) – normierter Score (siehe Algorithmik)
	•	persistence_s (INTEGER)
	•	status (TEXT) – candidate|confirmed|broken

Optional (für Debug):

orderbook_zones_history (rolling)
	•	gleiche Felder + Snapshot-Zeit, um Veränderungen nachvollziehen zu können

4.2 Orderblocks Tabelle

order_blocks_1h
	•	id (INTEGER PK)
	•	symbol (TEXT)
	•	direction (TEXT) – bullish|bearish
	•	created_ts_ms (INTEGER) – Zeit der OB-Kerze
	•	valid_from_ts_ms (INTEGER) – meist = created_ts_ms
	•	valid_to_ts_ms (INTEGER|null) – bis mitigated/invalid
	•	price_low (REAL)
	•	price_high (REAL)
	•	atr14 (REAL)
	•	bos_level (REAL) – Swing, der gebrochen wurde
	•	status (TEXT) – fresh|touched|invalid

⸻

5) Orderbook: Lokales L2-Buch korrekt pflegen (Pflichtprozess)

5.1 Initialisierung (Bootstrap)
	1.	WS öffnen: btceur@depth@100ms
	2.	Events puffern, merke erstes U
	3.	REST Snapshot holen (/api/v3/depth?limit=5000)  
	4.	Wenn snapshot.lastUpdateId < firstEvent.U: Snapshot erneut holen
	5.	Buffered Events: verwerfe Events mit u <= lastUpdateId
	6.	Setze lokales Buch auf Snapshot, book.updateId = lastUpdateId
	7.	Spiele buffered Events in Reihenfolge ab, dann live weiter

Das ist genau der Binance-Algorithmus. Wenn ihr das nicht macht, könnt ihr euch die gesamte Analyse sparen.  

5.2 Update-Regeln (pro depthUpdate Event)

Für jedes Event:
	•	Wenn u < book.updateId: ignore
	•	Wenn U > book.updateId + 1: Gap → Full Restart
	•	Für jedes (price, qty) in b und a:
	•	qty == 0 → remove price level
	•	else set/insert

⸻

6) Orderbook Analytics: Walls & Cluster-Zonen

6.1 Preprocessing / Binning

Orderbook ist tick-fein, für Zonen wollt ihr Binning:
	•	bin_size_eur Default: €50 (config)
	•	Preislevel wird auf Bin gerundet (floor für bids, ceil für asks oder standard rounding – config)

Warum: Sonst jagt ihr Rauschen und markiert 200 „Wände“.

6.2 Analyse-Range

Nur Bereich um den Marktpreis analysieren:
	•	range_pct Default: ±1.0% um mid
	•	Alles darüber ist für kurzfristige Reaktion irrelevant und kostet CPU.

6.3 Wall Detection (Single-Level)

Für jede Seite (bid/ask) nach Binning:
	•	vol_i = Sum(qty) im Bin i (oder notional)
	•	baseline_i = Median(vol_{i-k … i+k}) mit k=3 (config)
	•	wall_score_i = vol_i / max(baseline_i, eps)
	•	Wall-Kandidat, wenn wall_score_i >= wall_multiplier (Default 4.0)

6.4 Cluster-Zonen (mehrere Levels)
	•	Fasse benachbarte Wall-Kandidaten zusammen, wenn Abstand <= max_gap_bins (Default 1)
	•	Cluster-Zone:
	•	price_low = min(bin_low)
	•	price_high = max(bin_high)
	•	strength = weighted_avg(wall_score, notional)
	•	notional = Sum(qty*price) oder Sum(qty) (config)

6.5 Persistenz (damit es nicht Fake ist)

Ihr seid jetzt WS-basiert, also könnt ihr Persistenz wirklich tracken:
	•	Jede Zone bekommt first_seen_ts, last_seen_ts
	•	Zone gilt als confirmed, wenn:
	•	persistence_s >= 30s (Default)
	•	und strength bleibt über Threshold für mindestens X Publikationszyklen

Wenn Zone verschwindet:
	•	Wenn < 10s da war → status=discarded (nicht rendern)
	•	Sonst status=broken oder status=pulled (optional Unterscheidung, wenn Notional abrupt auf 0 fällt)

6.6 Publikationstakt (Wichtig für SQLite)

WS liefert 100ms. Ihr wollt nicht 10 writes/sec in SQLite.
	•	publish_interval_ms Default: 1000ms
	•	Streamer schreibt pro Sekunde:
	•	orderbook_metrics (eine Zeile)
	•	orderbook_zones_current (UPSERT pro Zone, idempotent)

⸻

7) Order Block Engine (1h) – berechenbarer Algorithmus

Ihr habt entschieden:
	•	k = 1.2 × ATR(14)
	•	Mitigation: sobald Preis Zone berührt

7.1 Inputs
	•	Quelle: btc_eur_1h (OHLCV)
	•	Minimum History für ATR(14) + Swing: 200 Kerzen empfohlen

7.2 ATR(14)
	•	True Range pro Kerze
	•	ATR als Wilder’s smoothing oder SMA – Default Wilder (config)

7.3 Swing Definition (Default)

Da du nichts dazu festgezurrt hast, setze ich als Default:
	•	Fractal Swing mit N=3:
	•	SwingHigh[t] wenn High[t] = max(High[t-3..t+3])
	•	SwingLow analog

(Als Config: N=5 für weniger Signale)

7.4 Displacement & BOS

Für jede Kerze t:
	•	range_t = high_t - low_t
	•	Displacement wenn range_t >= k * ATR_t (k=1.2)

Bullish BOS:
	•	Close[t] > lastSwingHigh.level

Bearish BOS:
	•	Close[t] < lastSwingLow.level

7.5 Order Block Definition

Bullish OB (Demand):
	•	Letzte bearishe Kerze vor dem Displacement-Up, in der Sequenz, die zum BOS führt
	•	Zone Default (konservativ): Open–Low der OB-Kerze
(Config-Option aggressiv: High–Low)

Bearish OB (Supply):
	•	Letzte bullishe Kerze vor Displacement-Down
	•	Zone Default (konservativ): High–Open
(Config aggressiv: High–Low)

7.6 Freshness / Mitigation
	•	Status initial: fresh
	•	Sobald Preis die Zone berührt:
	•	bullish: low <= price_high und high >= price_low (Touch)
	•	status → touched
	•	Optional: nach Touch entweder
	•	a) weiter rendern als “mitigated” bis invalid, oder
	•	b) ausblenden (Config render_touched=false Default: true, damit ihr es im Chart seht)

Invalidation (Default):
	•	Bullish OB invalid, wenn Candle-Close unter price_low
	•	Bearish OB invalid, wenn Candle-Close über price_high
