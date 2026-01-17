/**
 * Main Chart Controller for Bitcoin Trading Dashboard
 *
 * Handles TradingView Lightweight Charts initialization, data loading,
 * timeframe switching, and indicator management.
 */

let chart = null;
let candlestickSeries = null;
let currentTimeframe = '1h';
let autoRefreshInterval = null;

// Fixed candle limit - always use maximum
const CANDLE_LIMIT = 10000;

// Engulfing pattern visualization
let engulfingEnabled = false;
let engulfingMarkers = [];  // Array to store pattern markers

// Day analysis mode
let dayAnalysisEnabled = false;
let previousDayOpenLine = null;  // Previous day open price line
let previousDayCloseLine = null;  // Previous day close price line
let limitOrderLines = [];  // Open limit order price lines
let savedVisibleRange = null;  // Store original visible range before day mode

/**
 * Initialize TradingView charts
 */
function initChart() {
    const chartContainer = document.getElementById('chart-container');

    // Create main candlestick chart
    chart = LightweightCharts.createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: 500,
        layout: {
            background: { color: '#1a1a1a' },
            textColor: '#d1d4dc',
        },
        grid: {
            vertLines: { color: '#2a2a2a' },
            horzLines: { color: '#2a2a2a' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#3a3a3a',
        },
        timeScale: {
            borderColor: '#3a3a3a',
            timeVisible: true,
            secondsVisible: false,
        },
        localization: {
            timeFormatter: (timestamp) => {
                const date = new Date(timestamp * 1000);
                const hours = String(date.getUTCHours()).padStart(2, '0');
                const minutes = String(date.getUTCMinutes()).padStart(2, '0');
                return `${hours}:${minutes}`;
            },
        },
    });

    // Add candlestick series with visible wicks
    candlestickSeries = chart.addCandlestickSeries({
        upColor: '#00e676',
        downColor: '#ff4081',
        borderUpColor: '#00e676',
        borderDownColor: '#ff4081',
        // Make wicks brighter and more visible
        wickUpColor: '#69f0ae',      // Lighter green for up wicks
        wickDownColor: '#ff80ab',    // Lighter pink for down wicks
        wickVisible: true,
        borderVisible: true,
        priceLineVisible: false,
    });

    // Create tooltip element for displaying OHLC values
    const tooltip = document.createElement('div');
    tooltip.style.position = 'absolute';
    tooltip.style.display = 'none';
    tooltip.style.padding = '8px';
    tooltip.style.boxSizing = 'border-box';
    tooltip.style.fontSize = '12px';
    tooltip.style.textAlign = 'left';
    tooltip.style.zIndex = '1000';
    tooltip.style.top = '12px';
    tooltip.style.left = '12px';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.background = 'rgba(26, 26, 26, 0.95)';
    tooltip.style.color = '#d1d4dc';
    tooltip.style.borderRadius = '4px';
    tooltip.style.border = '1px solid #3a3a3a';
    tooltip.style.fontFamily = 'monospace';
    chartContainer.appendChild(tooltip);

    // Subscribe to crosshair move events to show OHLC data
    chart.subscribeCrosshairMove((param) => {
        if (
            param.point === undefined ||
            !param.time ||
            param.point.x < 0 ||
            param.point.y < 0
        ) {
            tooltip.style.display = 'none';
        } else {
            const data = param.seriesData.get(candlestickSeries);
            if (data) {
                const dateStr = new Date(data.time * 1000).toLocaleString('de-DE', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'UTC'
                });

                tooltip.style.display = 'block';
                tooltip.innerHTML = `
                    <div style="margin-bottom: 4px; font-weight: bold; color: #888;">Zeit: ${dateStr}</div>
                    <div style="color: #00e676;">O: ${data.open.toFixed(2)} €</div>
                    <div style="color: #69f0ae;">H: ${data.high.toFixed(2)} €</div>
                    <div style="color: #ff80ab;">L: ${data.low.toFixed(2)} €</div>
                    <div style="color: ${data.close >= data.open ? '#00e676' : '#ff4081'};">C: ${data.close.toFixed(2)} €</div>
                `;

                const y = param.point.y;
                const left = 12;
                const top = Math.max(12, Math.min(y - 50, chartContainer.clientHeight - 120));

                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            }
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartContainer.clientWidth });
    });

    console.log('Charts initialized');
}

/**
 * Load and display chart data for a specific timeframe
 *
 * @param {string} timeframe - Timeframe to load ('15m', '1h', '4h', '1d')
 * @param {number} limit - Number of candles to load
 * @param {object} preserveVisibleRange - Previous visible range to restore (optional)
 */
async function loadChartData(timeframe, limit = 1000, preserveVisibleRange = null) {
    showLoading();

    try {
        // Ensure charts are initialized
        if (!chart || !candlestickSeries) {
            console.error('Charts not initialized yet');
            hideLoading();
            return;
        }

        // Fetch OHLCV data
        const response = await API.fetchOHLCV(timeframe, limit);

        console.log('API Response:', response);
        console.log('Data length:', response.data ? response.data.length : 0);

        if (!response.data || response.data.length === 0) {
            console.error('No data received from API');
            alert('Keine Daten verfügbar für diesen Zeitrahmen');
            hideLoading();
            return;
        }

        console.log('First candle:', response.data[0]);

        // Update candlestick series
        candlestickSeries.setData(response.data);

        // Restore visible range IMMEDIATELY after setting data (before it auto-fits)
        if (preserveVisibleRange) {
            try {
                chart.timeScale().setVisibleRange(preserveVisibleRange);
                console.log('Restored visible range immediately after setData:', preserveVisibleRange);
            } catch (error) {
                console.warn('Could not restore visible range immediately:', error.message);
            }
        }

        // Update info panel
        updateChartInfo(response);

        // Update latest price
        await updateLatestPrice(timeframe);

        // Restore previous visible range again (in case updateLatestPrice modified it)
        try {
            if (preserveVisibleRange) {
                // Restore the previous visible range to keep chart position
                chart.timeScale().setVisibleRange(preserveVisibleRange);
                console.log('Restored visible range at end:', preserveVisibleRange);
            } else {
                // Only fit content if no range to preserve (initial load)
                chart.timeScale().fitContent();
            }
        } catch (error) {
            console.warn('Could not restore/fit visible range:', error.message);
        }

        hideLoading();
        console.log(`Loaded ${response.count} candles for ${timeframe}`);
    } catch (error) {
        console.error('Error loading chart data:', error);
        console.error('Error details:', error.message, error.stack);
        hideLoading();
        alert('Fehler beim Laden der Chart-Daten.\n\nDetails: ' + error.message + '\n\nBitte öffne die Browser-Konsole (F12) für weitere Informationen.');
    }
}

/**
 * Update latest price display in header
 *
 * @param {string} timeframe - Current timeframe
 */
async function updateLatestPrice(timeframe) {
    try {
        const data = await API.fetchLatestPrice(timeframe);

        // Format price
        const priceValue = document.getElementById('price-value');
        priceValue.textContent = `€${data.close.toLocaleString('de-DE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;

        // Format change percentage
        const changeElement = document.getElementById('price-change');
        if (data.change_percent !== null) {
            const changeText = `${data.change_percent > 0 ? '+' : ''}${data.change_percent.toFixed(2)}%`;
            changeElement.textContent = changeText;
            changeElement.className = `price-change ${data.change_percent >= 0 ? 'positive' : 'negative'}`;
        } else {
            changeElement.textContent = '';
            changeElement.className = 'price-change';
        }
    } catch (error) {
        console.error('Error updating latest price:', error);
    }
}

/**
 * Update chart info panel (candle count, date range)
 *
 * @param {Object} response - API response with chart data
 */
function updateChartInfo(response) {
    // Don't update if day analysis is active (it manages its own display)
    if (dayAnalysisEnabled) {
        console.log('[updateChartInfo] Skipping - day analysis is active');
        return;
    }

    const countText = response.count.toLocaleString('de-DE');

    // Show if we hit the limit
    const limitInfo = response.count >= CANDLE_LIMIT ? ` (max)` : '';
    document.getElementById('candle-count').textContent = countText + limitInfo;

    if (response.data.length > 0) {
        const firstTime = new Date(response.data[0].time * 1000);
        const lastTime = new Date(response.data[response.data.length - 1].time * 1000);

        document.getElementById('date-range').textContent =
            `${firstTime.toLocaleDateString('de-DE')} - ${lastTime.toLocaleDateString('de-DE')}`;
    }
}

/**
 * Show loading indicator
 */
function showLoading() {
    document.getElementById('loading-indicator').classList.remove('hidden');
}

/**
 * Hide loading indicator
 */
function hideLoading() {
    document.getElementById('loading-indicator').classList.add('hidden');
}

/**
 * Handle timeframe change event
 *
 * @param {string} timeframe - New timeframe
 */
async function onTimeframeChange(timeframe) {
    currentTimeframe = timeframe;

    // Save current visible time range to restore after loading new data
    let visibleRange = null;
    try {
        visibleRange = chart.timeScale().getVisibleRange();
    } catch (error) {
        console.debug('Could not save visible range:', error);
    }

    await loadChartData(timeframe, CANDLE_LIMIT, visibleRange);

    // Reload active indicators
    const indicators = getActiveIndicators();
    for (const [indicator, checkbox] of Object.entries(indicators)) {
        if (checkbox.checked) {
            await toggleIndicator(indicator, true);
        }
    }

    // Reload engulfing patterns if enabled
    if (engulfingEnabled) {
        await loadAndDisplayEngulfing();
    }

    // Reload day analysis if enabled
    if (dayAnalysisEnabled) {
        await enableDayAnalysis();
    }
}


/**
 * Get all indicator checkbox elements
 *
 * @returns {Object} Dictionary of indicator checkboxes
 */
function getActiveIndicators() {
    return {
        rsi: document.getElementById('rsi-toggle'),
        sma: document.getElementById('sma-toggle'),
        ema: document.getElementById('ema-toggle'),
        bb: document.getElementById('bb-toggle'),
    };
}

/**
 * Toggle indicator on/off
 *
 * @param {string} indicator - Indicator type ('rsi', 'sma', 'ema', 'bb')
 * @param {boolean} enabled - Whether to enable or disable
 */
async function toggleIndicator(indicator, enabled) {
    if (enabled) {
        switch (indicator) {
            case 'rsi':
                await IndicatorManager.addRSI(chart, currentTimeframe);
                break;
            case 'sma':
                await IndicatorManager.addSMA(chart, currentTimeframe);
                break;
            case 'ema':
                await IndicatorManager.addEMA(chart, currentTimeframe);
                break;
            case 'bb':
                await IndicatorManager.addBollingerBands(chart, currentTimeframe);
                break;
        }
    } else {
        IndicatorManager.removeIndicator(chart, indicator);
    }
}

/**
 * Start auto-refresh (always active)
 */
function startAutoRefresh() {
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }

    // Start auto-refresh
    autoRefreshInterval = setInterval(async () => {
        console.log('Auto-refreshing chart data...');

        // Save current zoom/position before refresh
        let savedRange = null;
        try {
            savedRange = chart.timeScale().getVisibleRange();
            console.log('Saved visible range:', savedRange);
        } catch (error) {
            console.warn('Could not save visible range:', error);
        }

        // Reload chart with preserved zoom
        await loadChartData(currentTimeframe, CANDLE_LIMIT, savedRange);

        // Reload active indicators
        const indicators = getActiveIndicators();
        for (const [indicator, checkbox] of Object.entries(indicators)) {
            if (checkbox.checked) {
                await toggleIndicator(indicator, true);
            }
        }

        // If day analysis was active, re-enable it (this will override saved range)
        if (dayAnalysisEnabled) {
            console.log('Re-enabling day analysis after 60s auto-refresh');
            await enableDayAnalysis();
        } else if (savedRange) {
            // Otherwise restore zoom
            try {
                chart.timeScale().setVisibleRange(savedRange);
                console.log('Restored zoom after 60s auto-refresh');
            } catch (error) {
                console.warn('Could not restore zoom after indicators:', error);
            }
        }
    }, 60000); // Refresh every 60 seconds

    console.log('Auto-refresh started (60s interval)');
}

/**
 * Initialize all event listeners
 */
function initEventListeners() {
    // Timeframe selector
    document.getElementById('timeframe-select').addEventListener('change', (e) => {
        onTimeframeChange(e.target.value);
    });

    // Indicator toggles
    const indicators = getActiveIndicators();
    for (const [indicator, checkbox] of Object.entries(indicators)) {
        checkbox.addEventListener('change', (e) => {
            toggleIndicator(indicator, e.target.checked);
        });
    }

    // Database update button
    document.getElementById('update-db-btn').addEventListener('click', async () => {
        await updateDatabase();
    });
}

/**
 * Core database update function - fetches latest data from Binance
 * @returns {Promise<{success: boolean, data?: any, error?: string}>}
 */
async function fetchDatabaseUpdate() {
    try {
        const response = await fetch('/api/update-database/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();
        return { success: data.success, data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

/**
 * Update database from Binance (with confirmation and UI feedback)
 */
async function updateDatabase() {
    const button = document.getElementById('update-db-btn');
    const originalText = button.textContent;

    if (confirm('Neue Daten von Binance laden?\n\nDies kann 1-2 Minuten dauern.')) {
        try {
            button.disabled = true;
            button.textContent = '⏳ Lade Daten...';

            const result = await fetchDatabaseUpdate();

            if (result.success) {
                button.textContent = '🔄 Aktualisiere Chart...';

                // Save current zoom/position before refresh
                let savedRange = null;
                try {
                    savedRange = chart.timeScale().getVisibleRange();
                } catch (error) {
                    console.warn('Could not save visible range:', error);
                }

                // Reload chart data with preserved zoom
                await loadChartData(currentTimeframe, CANDLE_LIMIT, savedRange);

                // Reload active indicators
                const indicators = getActiveIndicators();
                for (const [indicator, checkbox] of Object.entries(indicators)) {
                    if (checkbox.checked) {
                        await toggleIndicator(indicator, true);
                    }
                }

                // If day analysis was active, re-enable it (this will override saved range)
                if (dayAnalysisEnabled) {
                    console.log('Re-enabling day analysis after manual update');
                    await enableDayAnalysis();
                } else if (savedRange) {
                    // Otherwise restore zoom
                    try {
                        chart.timeScale().setVisibleRange(savedRange);
                        console.log('Restored zoom after manual update');
                    } catch (error) {
                        console.warn('Could not restore zoom after indicators:', error);
                    }
                }

                button.textContent = '✅ Erfolgreich!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);

                console.log('✅ Database updated and chart reloaded');
            } else {
                console.error('Update failed:', result.data);
                const errorMsg = result.error || result.data?.error || result.data?.message || 'Unknown error';
                alert(`❌ Fehler beim Aktualisieren:\n\n${errorMsg}\n\nDetails in der Konsole (F12)`);
            }
        } catch (error) {
            console.error('Error updating database:', error);
            alert(`❌ Fehler beim Aktualisieren:\n\n${error.message}`);
        } finally {
            button.disabled = false;
        }
    }
}

/**
 * Update database from Binance silently (no confirmation, no reload popup)
 * Used internally by day analysis mode
 * @returns {Promise<boolean>} True if update succeeded
 */
async function updateDatabaseSilent() {
    console.log('Fetching latest data from Binance...');

    const result = await fetchDatabaseUpdate();

    if (result.success) {
        console.log('✅ Database updated successfully');
        return true;
    } else {
        console.error('Database update failed:', result.data || result.error);
        return false;
    }
}

/**
 * Initialize dashboard on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Bitcoin Trading Dashboard initializing...');

    try {
        console.log('Step 1: Initializing charts...');
        initChart();

        console.log('Step 2: Initializing event listeners...');
        initEventListeners();

        console.log('Step 3: Loading chart data for timeframe:', currentTimeframe, 'with limit:', CANDLE_LIMIT);
        await loadChartData(currentTimeframe, CANDLE_LIMIT);

        console.log('Step 4: Starting auto-refresh...');
        startAutoRefresh();

        console.log('Dashboard ready!');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        console.error('Error details:', error.message, error.stack);
        alert('Fehler beim Initialisieren des Dashboards\n\nDetails: ' + error.message + '\n\nBitte öffne die Browser-Konsole (F12) für weitere Informationen.');
    }
});

/**
 * Toggle engulfing pattern visualization on/off
 */
async function toggleEngulfing() {
    engulfingEnabled = !engulfingEnabled;
    const button = document.getElementById('engulfing-toggle');

    if (engulfingEnabled) {
        button.classList.add('active');
        button.textContent = '🔄 Engulfing: AN';
        await loadAndDisplayEngulfing();
    } else {
        button.classList.remove('active');
        button.textContent = '🔄 Engulfing: AUS';
        clearEngulfing();
    }
}

/**
 * Load engulfing patterns from API and display on chart
 */
async function loadAndDisplayEngulfing() {
    try {
        const limit = CANDLE_LIMIT;
        const response = await fetch(`/api/engulfing/${currentTimeframe}/?limit=${limit}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log(`Loaded ${data.count} engulfing patterns for ${currentTimeframe}`);

        // Display patterns as markers on chart
        displayEngulfingMarkers(data.patterns);

    } catch (error) {
        console.error('Error loading engulfing patterns:', error);
        alert(`Fehler beim Laden der Engulfing Patterns:\n${error.message}`);
    }
}

/**
 * Display engulfing patterns as markers on the candlestick chart
 */
function displayEngulfingMarkers(patterns) {
    if (!candlestickSeries || !patterns || patterns.length === 0) {
        console.log('No engulfing patterns to display');
        return;
    }

    // Convert patterns to TradingView markers format
    const markers = patterns.map(pattern => {
        const isBullish = pattern.pattern_type === 'bullish_engulfing';

        return {
            time: pattern.time,
            position: isBullish ? 'belowBar' : 'aboveBar',
            color: isBullish ? '#00c853' : '#ff5252',
            shape: isBullish ? 'arrowUp' : 'arrowDown',
            text: isBullish ? 'BE' : 'BE',  // Bullish/Bearish Engulfing
            size: pattern.strength > 1.5 ? 2 : 1  // Bigger marker for stronger patterns
        };
    });

    // Get existing markers and filter out old engulfing markers
    const existingMarkers = candlestickSeries.markers() || [];
    const filteredExisting = existingMarkers.filter(m => m.text !== 'BE');

    // Combine filtered existing with new engulfing markers
    const combinedMarkers = [...filteredExisting, ...markers];

    // Set combined markers on the candlestick series
    candlestickSeries.setMarkers(combinedMarkers);
    engulfingMarkers = patterns;

    console.log(`Displayed ${markers.length} engulfing pattern markers on chart (total markers: ${combinedMarkers.length})`);
}

/**
 * Clear all engulfing pattern markers from chart
 */
function clearEngulfing() {
    if (!candlestickSeries) return;

    // Remove only engulfing markers (keep other markers like swing points)
    const existingMarkers = candlestickSeries.markers() || [];
    const filteredMarkers = existingMarkers.filter(m => m.text !== 'BE');

    candlestickSeries.setMarkers(filteredMarkers);
    engulfingMarkers = [];

    console.log('Cleared engulfing pattern markers from chart (kept other markers)');
}

/**
 * Toggle day analysis mode on/off
 */
async function toggleDayAnalysis() {
    dayAnalysisEnabled = !dayAnalysisEnabled;
    const button = document.getElementById('day-analysis-toggle');

    if (dayAnalysisEnabled) {
        // Show loading state
        button.disabled = true;
        button.textContent = '📅 Lädt...';

        // 1. Update database silently to get latest data
        console.log('Day analysis mode: Fetching latest data from Binance...');
        await updateDatabaseSilent();

        // 2. Reload chart data
        console.log('Day analysis mode: Reloading chart data...');
        await loadChartData(currentTimeframe, CANDLE_LIMIT);

        // 3. Enable day analysis
        button.classList.add('active');
        button.textContent = '📅 Heute: AN';
        button.disabled = false;
        await enableDayAnalysis();
    } else {
        button.classList.remove('active');
        button.textContent = '📅 Heute: AUS';
        disableDayAnalysis();
    }
}

/**
 * Enable day analysis mode
 * - Sets visible range to current day + previous day
 * - Draws previous day open/close reference lines
 */
async function enableDayAnalysis() {
    if (!candlestickSeries) {
        console.error('Chart not initialized');
        return;
    }

    try {
        // Save current visible range to restore later
        try {
            savedVisibleRange = chart.timeScale().getVisibleRange();
        } catch (error) {
            console.debug('Could not save current visible range:', error);
        }

        // Get all data from the candlestick series
        const allData = candlestickSeries.data();
        if (!allData || allData.length === 0) {
            console.warn('No chart data available for day analysis');
            return;
        }

        // Calculate time boundaries (current day start, yesterday start) in UTC
        const now = new Date();
        const todayStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0));
        const yesterdayStart = new Date(todayStart);
        yesterdayStart.setUTCDate(yesterdayStart.getUTCDate() - 1);

        const todayStartUnix = Math.floor(todayStart.getTime() / 1000);
        const yesterdayStartUnix = Math.floor(yesterdayStart.getTime() / 1000);

        console.log('Day analysis time range:', {
            yesterdayStart: new Date(yesterdayStartUnix * 1000).toISOString(),
            todayStart: new Date(todayStartUnix * 1000).toISOString(),
            now: now.toISOString()
        });

        // Find data for yesterday and today
        const yesterdayData = allData.filter(d => d.time >= yesterdayStartUnix && d.time < todayStartUnix);
        const todayData = allData.filter(d => d.time >= todayStartUnix);

        console.log(`Found ${yesterdayData.length} candles for yesterday, ${todayData.length} for today`);

        if (yesterdayData.length === 0) {
            alert('Keine Daten für den Vortag gefunden.\n\nTipp: Verwenden Sie 15m oder 1h Timeframe für Tagesanalyse.');
            dayAnalysisEnabled = false;
            const button = document.getElementById('day-analysis-toggle');
            button.classList.remove('active');
            button.textContent = '📅 Heute: AUS';
            return;
        }

        // Get previous day open (first candle) and close (last candle)
        const prevDayOpen = yesterdayData[0].open;
        const prevDayClose = yesterdayData[yesterdayData.length - 1].close;

        console.log('Previous day levels:', {
            open: prevDayOpen,
            close: prevDayClose
        });

        // Calculate min and max prices from TODAY ONLY (not yesterday)
        let minPrice = Infinity;
        let maxPrice = -Infinity;

        todayData.forEach(candle => {
            if (candle.low < minPrice) minPrice = candle.low;
            if (candle.high > maxPrice) maxPrice = candle.high;
        });

        // Include previous day open/close in price range for better context
        if (prevDayOpen < minPrice) minPrice = prevDayOpen;
        if (prevDayOpen > maxPrice) maxPrice = prevDayOpen;
        if (prevDayClose < minPrice) minPrice = prevDayClose;
        if (prevDayClose > maxPrice) maxPrice = prevDayClose;

        // Add 2% padding for better visibility
        const priceRange = maxPrice - minPrice;
        const padding = priceRange * 0.02;
        const paddedMin = minPrice - padding;
        const paddedMax = maxPrice + padding;

        console.log('Price range for TODAY only:', {
            min: minPrice,
            max: maxPrice,
            paddedMin: paddedMin,
            paddedMax: paddedMax,
            includesPrevDayLevels: true
        });

        // IMPORTANT: Adjust ALL timestamps for UTC display
        // TradingView displays timestamps in local time, but we want UTC
        // For UTC+1: getTimezoneOffset() returns -60 minutes = -3600 seconds
        // We need to SUBTRACT the offset to compensate (subtracting negative = adding)
        // This shifts timestamps forward: 16:00 → 17:00 (correct UTC time)
        const timezoneOffsetSeconds = new Date().getTimezoneOffset() * 60; // Convert minutes to seconds (negative for UTC+)

        // Update chart with ONLY yesterday + today data (not all 10,000 candles)
        const combinedData = [...yesterdayData, ...todayData].map(candle => ({
            ...candle,
            time: candle.time - timezoneOffsetSeconds  // SUBTRACT offset (for UTC+1: subtracts -3600 = adds 3600)
        }));
        candlestickSeries.setData(combinedData);
        console.log(`Set chart data to ${combinedData.length} candles (yesterday + today only)`);

        // Set visible range to TODAY ONLY (midnight → now) - also adjust these timestamps!
        const visibleFrom = todayStartUnix - timezoneOffsetSeconds;
        const visibleTo = Math.floor(now.getTime() / 1000) - timezoneOffsetSeconds;

        chart.timeScale().setVisibleRange({
            from: visibleFrom,
            to: visibleTo
        });

        // Draw horizontal lines for previous day open/close - use adjusted timestamp!
        const adjustedTodayStart = todayStartUnix - timezoneOffsetSeconds;
        // drawPreviousDayLines(prevDayOpen, prevDayClose, adjustedTodayStart);  // REMOVED: User requested to remove previous day Open/Close lines

        // Fetch and draw open limit orders (filtered to ±15% of today's range) - use adjusted timestamp!
        await drawOpenLimitOrders(adjustedTodayStart, minPrice, maxPrice);

        // After drawing all lines, fit content to visible time range
        console.log('Auto-fitting chart to TODAY range');

        console.log('Day analysis mode enabled - showing TODAY only');

        // Update date range display to show only TODAY
        const totalCandles = todayData.length;
        const dateRangeText = `Heute: ${todayStart.toLocaleDateString('de-DE')}`;

        console.log('[enableDayAnalysis] Updating UI - Date range:', dateRangeText, 'Candles:', totalCandles);

        document.getElementById('date-range').textContent = dateRangeText;
        document.getElementById('candle-count').textContent = totalCandles.toLocaleString('de-DE');

        console.log('[enableDayAnalysis] ✅ UI updated successfully');

    } catch (error) {
        console.error('Error enabling day analysis:', error);
        alert(`Fehler beim Aktivieren der Tagesanalyse:\n${error.message}`);
    }
}

/**
 * Draw horizontal reference lines for previous day open/close
 */
function drawPreviousDayLines(openPrice, closePrice, fromTime) {
    if (!chart) return;

    // Remove old lines if they exist
    clearPreviousDayLines();

    // Create line series for previous day open (yellow)
    previousDayOpenLine = chart.addLineSeries({
        color: '#f9a825',  // Dark yellow/gold
        lineWidth: 2,
        lineStyle: 2,  // Dashed line
        crosshairMarkerVisible: true,
        lastValueVisible: true,
        priceLineVisible: true,
        title: 'Vortag Open'
    });

    // Create line series for previous day close (yellow)
    previousDayCloseLine = chart.addLineSeries({
        color: '#fdd835',  // Bright yellow
        lineWidth: 2,
        lineStyle: 2,  // Dashed line
        crosshairMarkerVisible: true,
        lastValueVisible: true,
        priceLineVisible: true,
        title: 'Vortag Close'
    });

    // Create data points extending from today's start to far future
    const futureTime = fromTime + (86400 * 30);  // Extend 30 days into future

    const openLineData = [
        { time: fromTime, value: openPrice },
        { time: futureTime, value: openPrice }
    ];

    const closeLineData = [
        { time: fromTime, value: closePrice },
        { time: futureTime, value: closePrice }
    ];

    previousDayOpenLine.setData(openLineData);
    previousDayCloseLine.setData(closeLineData);

    console.log('Drew previous day reference lines:', {
        open: openPrice,
        close: closePrice,
        fromTime: new Date(fromTime * 1000).toISOString()
    });
}

/**
 * Fetch and draw open limit orders as price lines
 * @param {number} fromTime - Start time for line display
 * @param {number} minPrice - Minimum price for filtering orders
 * @param {number} maxPrice - Maximum price for filtering orders
 */
async function drawOpenLimitOrders(fromTime, minPrice = null, maxPrice = null) {
    if (!chart) return;

    // Clear old limit order lines
    clearLimitOrderLines();

    try {
        // Fetch open orders from API
        const response = await fetch('/api/sync-open-orders/');
        if (!response.ok) {
            console.warn('Could not fetch open orders:', response.status);
            return;
        }

        const data = await response.json();

        if (!data || !data.total_open_orders || data.total_open_orders === 0) {
            console.log('No open limit orders to display');
            return;
        }

        // Fetch detailed order data from database via cashflow API
        // (We need to get individual order details)
        const cashflowResponse = await fetch('/api/cashflow/?limit=1000&days=1');
        if (!cashflowResponse.ok) {
            console.warn('Could not fetch order details');
            return;
        }

        const cashflowData = await cashflowResponse.json();
        let openOrders = cashflowData.transactions.filter(tx =>
            tx.status === 'open' && (tx.type === 'limit_buy' || tx.type === 'limit_sell')
        );

        console.log(`Found ${openOrders.length} open limit orders total`);

        // Filter orders: Only show orders within ±15% of today's price range
        if (minPrice !== null && maxPrice !== null) {
            const priceRange = maxPrice - minPrice;
            const filterMin = minPrice - (priceRange * 0.15);
            const filterMax = maxPrice + (priceRange * 0.15);

            const beforeFilter = openOrders.length;
            openOrders = openOrders.filter(order => {
                const price = order.price;
                return price >= filterMin && price <= filterMax;
            });

            const filtered = beforeFilter - openOrders.length;
            console.log(`Filtered ${filtered} orders outside visible range (${filterMin.toFixed(0)}-${filterMax.toFixed(0)} EUR)`);
        }

        console.log(`Drawing ${openOrders.length} open limit orders in visible range`);

        // Extend line to future
        const futureTime = fromTime + (86400 * 30);  // 30 days ahead

        // Draw each order as a horizontal line
        openOrders.forEach((order, index) => {
            const isBuy = order.type === 'limit_buy';
            const price = order.price;
            const btcAmount = Math.abs(order.amount_btc);

            // Create line series
            const lineSeries = chart.addLineSeries({
                color: isBuy ? '#26a69a' : '#ef5350',  // Green for buy, red for sell
                lineWidth: 2,
                lineStyle: 1,  // Dashed line (LineStyle.Dashed = 1)
                crosshairMarkerVisible: true,
                lastValueVisible: true,
                priceLineVisible: true,
                title: `${isBuy ? 'Buy' : 'Sell'} ${btcAmount.toFixed(4)} BTC @ €${price.toFixed(2)}`
            });

            // Set line data
            const lineData = [
                { time: fromTime, value: price },
                { time: futureTime, value: price }
            ];

            lineSeries.setData(lineData);
            limitOrderLines.push(lineSeries);

            console.log(`Drew ${isBuy ? 'buy' : 'sell'} limit line at €${price.toFixed(2)} for ${btcAmount.toFixed(4)} BTC`);
        });

        console.log(`Drew ${limitOrderLines.length} limit order lines`);

    } catch (error) {
        console.error('Error drawing limit orders:', error);
    }
}

/**
 * Clear limit order lines
 */
function clearLimitOrderLines() {
    limitOrderLines.forEach(line => {
        try {
            chart.removeSeries(line);
        } catch (error) {
            console.debug('Error removing limit order line:', error);
        }
    });
    limitOrderLines = [];
}

/**
 * Clear previous day reference lines
 */
function clearPreviousDayLines() {
    if (previousDayOpenLine) {
        try {
            chart.removeSeries(previousDayOpenLine);
        } catch (error) {
            console.debug('Error removing previous day open line:', error);
        }
        previousDayOpenLine = null;
    }

    if (previousDayCloseLine) {
        try {
            chart.removeSeries(previousDayCloseLine);
        } catch (error) {
            console.debug('Error removing previous day close line:', error);
        }
        previousDayCloseLine = null;
    }

    console.log('Cleared previous day reference lines');
}

/**
 * Disable day analysis mode
 * - Removes previous day lines
 * - Restores original visible range
 * - Re-enables auto-scaling
 */
function disableDayAnalysis() {
    // Set flag to false
    dayAnalysisEnabled = false;
    console.log('[disableDayAnalysis] Day analysis disabled');

    // Remove reference lines
    // clearPreviousDayLines();  // REMOVED: User requested to remove previous day Open/Close lines
    clearLimitOrderLines();

    // Re-enable auto-scaling for price axis
    if (chart && candlestickSeries) {
        try {
            chart.priceScale('right').applyOptions({
                autoScale: true
            });

            candlestickSeries.priceScale().applyOptions({
                autoScale: true
            });

            console.log('Re-enabled auto-scaling for price axis');
        } catch (error) {
            console.debug('Error re-enabling auto-scale:', error);
        }
    }

    // Restore original visible range
    if (savedVisibleRange && chart) {
        try {
            chart.timeScale().setVisibleRange(savedVisibleRange);
            console.log('Restored original visible range');
        } catch (error) {
            console.debug('Could not restore visible range, fitting content instead:', error);
            chart.timeScale().fitContent();
        }
        savedVisibleRange = null;
    } else if (chart) {
        // No saved range, just fit content
        chart.timeScale().fitContent();
    }

    // Reload chart data to update UI with full date range
    loadChartData(currentTimeframe, CANDLE_LIMIT).catch(error => {
        console.error('Error reloading chart data after disabling day analysis:', error);
    });

    console.log('Day analysis mode disabled');
}


// ==================== AUTO-UPDATE STATUS ====================

let autoUpdateNextRunTime = null;
let autoUpdateCountdownInterval = null;
let lastKnownUpdateTimestamp = null;

/**
 * Update auto-update status indicator
 */
async function updateAutoUpdateStatus() {
    try {
        const status = await API.fetchAutoUpdateStatus();
        const indicator = document.getElementById('auto-update-indicator');
        const textElement = document.getElementById('auto-update-text');

        if (!status) {
            textElement.textContent = 'Unbekannt';
            indicator.textContent = '❓';
            return;
        }

        if (!status.enabled) {
            textElement.textContent = 'Auto-Update deaktiviert';
            indicator.textContent = '⏸️';
            indicator.style.color = '#888';
            textElement.style.color = '#888';
            return;
        }

        if (status.scheduler && status.scheduler.running && status.scheduler.jobs.length > 0) {
            // Check if new data was added (auto-update completed)
            if (status.last_updates && status.last_updates[currentTimeframe]) {
                const updateInfo = status.last_updates[currentTimeframe];
                const currentTimestamp = updateInfo.timestamp;

                // If timestamp changed and status is success, reload chart
                if (lastKnownUpdateTimestamp &&
                    currentTimestamp !== lastKnownUpdateTimestamp &&
                    updateInfo.status === 'success' &&
                    updateInfo.inserted > 0) {
                    console.log(`🔄 New data detected (${updateInfo.inserted} candles), reloading chart...`);

                    // Save current zoom/position before refresh
                    let savedRange = null;
                    try {
                        savedRange = chart.timeScale().getVisibleRange();
                    } catch (error) {
                        console.warn('Could not save visible range:', error);
                    }

                    // Reload chart with preserved zoom
                    await loadChartData(currentTimeframe, CANDLE_LIMIT, savedRange);

                    // Reload active indicators
                    const indicators = getActiveIndicators();
                    for (const [indicator, checkbox] of Object.entries(indicators)) {
                        if (checkbox.checked) {
                            await toggleIndicator(indicator, true);
                        }
                    }

                    // If day analysis was active, re-enable it (this will override saved range)
                    if (dayAnalysisEnabled) {
                        console.log('Re-enabling day analysis after auto-update');
                        await enableDayAnalysis();
                    } else if (savedRange) {
                        // Otherwise restore zoom
                        try {
                            chart.timeScale().setVisibleRange(savedRange);
                            console.log('Restored saved zoom after auto-update');
                        } catch (error) {
                            console.warn('Could not restore zoom after indicators:', error);
                        }
                    }
                }

                // Update last known timestamp
                lastKnownUpdateTimestamp = currentTimestamp;
            }

            // Find the job for current timeframe (or first job)
            const relevantJob = status.scheduler.jobs.find(job => job.id === `update_${currentTimeframe}`)
                             || status.scheduler.jobs[0];

            if (relevantJob && relevantJob.next_run) {
                autoUpdateNextRunTime = new Date(relevantJob.next_run);
                indicator.textContent = '✅';
                indicator.style.color = '#4CAF50';
                textElement.style.color = '#4CAF50';

                // Start countdown
                updateCountdown();

                // Clear old interval if exists
                if (autoUpdateCountdownInterval) {
                    clearInterval(autoUpdateCountdownInterval);
                }

                // Update countdown every second
                autoUpdateCountdownInterval = setInterval(updateCountdown, 1000);
            } else {
                textElement.textContent = 'Aktiv';
                indicator.textContent = '✅';
                indicator.style.color = '#4CAF50';
                textElement.style.color = '#4CAF50';
            }
        } else {
            textElement.textContent = 'Inaktiv';
            indicator.textContent = '❌';
            indicator.style.color = '#f44336';
            textElement.style.color = '#f44336';
        }
    } catch (error) {
        console.error('Error updating auto-update status:', error);
        const indicator = document.getElementById('auto-update-indicator');
        const textElement = document.getElementById('auto-update-text');
        textElement.textContent = 'Fehler beim Abrufen';
        indicator.textContent = '⚠️';
        indicator.style.color = '#ff9800';
        textElement.style.color = '#ff9800';
    }
}

/**
 * Update countdown display
 */
function updateCountdown() {
    if (!autoUpdateNextRunTime) return;

    const now = new Date();
    const diff = autoUpdateNextRunTime - now;

    if (diff <= 0) {
        // Update is happening now or overdue
        const textElement = document.getElementById('auto-update-text');
        textElement.textContent = 'Update läuft...';

        // Refresh status in 10 seconds
        setTimeout(() => {
            updateAutoUpdateStatus();
        }, 10000);

        return;
    }

    // Calculate time remaining
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);

    const textElement = document.getElementById('auto-update-text');

    if (minutes > 0) {
        textElement.textContent = `Nächstes Update in ${minutes}min ${seconds}s`;
    } else {
        textElement.textContent = `Nächstes Update in ${seconds}s`;
    }
}

// Initialize auto-update status on page load
document.addEventListener('DOMContentLoaded', () => {
    updateAutoUpdateStatus();

    // Refresh status every 30 seconds
    setInterval(updateAutoUpdateStatus, 30000);
});
