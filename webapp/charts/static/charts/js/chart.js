/**
 * Main Chart Controller for Bitcoin Trading Dashboard
 *
 * Handles TradingView Lightweight Charts initialization, data loading,
 * timeframe switching, and indicator management.
 */

let chart = null;
let candlestickSeries = null;
let volumeSeries = null;
let volumeChart = null;
let currentTimeframe = '1h';
let autoRefreshInterval = null;
let isLoadingMore = false;
let allDataLoaded = false;
let currentDataLength = 0;

// Fixed candle limit - always use maximum
const CANDLE_LIMIT = 10000;

// Gap visualization
let gapsEnabled = false;
let gapType = 'regular';  // 'regular' or 'fvg'
let gapSeries = [];  // Array to store gap rectangle series

// Engulfing pattern visualization
let engulfingEnabled = false;
let engulfingMarkers = [];  // Array to store pattern markers

// Trend analysis visualization
let trendEnabled = false;
let trendLineSeries = null;  // Main trendline
let swingPointMarkers = [];  // Swing high/low markers
let trendData = null;  // Cached trend data

// Day analysis mode
let dayAnalysisEnabled = false;
let previousDayOpenLine = null;  // Previous day open price line
let previousDayCloseLine = null;  // Previous day close price line
let savedVisibleRange = null;  // Store original visible range before day mode

/**
 * Initialize TradingView charts (main + volume)
 */
function initChart() {
    const chartContainer = document.getElementById('chart-container');
    const volumeContainer = document.getElementById('volume-container');

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
    });

    // Add candlestick series with visible wicks
    candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderUpColor: '#26a69a',
        borderDownColor: '#ef5350',
        // Make wicks brighter and more visible
        wickUpColor: '#4dd0c5',      // Lighter cyan for up wicks
        wickDownColor: '#ff6b6b',    // Lighter red for down wicks
        wickVisible: true,
        borderVisible: true,
        priceLineVisible: false,
    });

    // Create separate volume chart
    volumeChart = LightweightCharts.createChart(volumeContainer, {
        width: volumeContainer.clientWidth,
        height: 150,
        layout: {
            background: { color: '#1a1a1a' },
            textColor: '#d1d4dc',
        },
        grid: {
            vertLines: { color: '#2a2a2a' },
            horzLines: { color: '#2a2a2a' },
        },
        timeScale: {
            borderColor: '#3a3a3a',
            visible: true,
            timeVisible: true,
        },
        rightPriceScale: {
            borderColor: '#3a3a3a',
        },
    });

    // Add volume histogram series
    volumeSeries = volumeChart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: '',
    });

    // Synchronize time scales
    chart.timeScale().subscribeVisibleTimeRangeChange(() => {
        try {
            const timeRange = chart.timeScale().getVisibleRange();
            if (timeRange && volumeChart && volumeChart.timeScale()) {
                volumeChart.timeScale().setVisibleRange(timeRange);
            }
        } catch (error) {
            // Ignore synchronization errors during initialization
            console.debug('Time scale sync skipped:', error.message);
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        chart.applyOptions({ width: chartContainer.clientWidth });
        volumeChart.applyOptions({ width: volumeContainer.clientWidth });
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
        if (!chart || !candlestickSeries || !volumeSeries) {
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

        // Track current data length
        currentDataLength = response.data.length;
        allDataLoaded = response.data.length < limit;

        // Update candlestick series
        candlestickSeries.setData(response.data);

        // Update volume series
        const volumeData = response.data.map(d => ({
            time: d.time,
            value: d.volume,
            color: d.close >= d.open ? '#26a69a' : '#ef5350',
        }));
        volumeSeries.setData(volumeData);

        // Update info panel
        updateChartInfo(response);

        // Update latest price
        await updateLatestPrice(timeframe);

        // Restore previous visible range or fit content
        try {
            if (preserveVisibleRange) {
                // Restore the previous visible range to keep chart position
                chart.timeScale().setVisibleRange(preserveVisibleRange);
                volumeChart.timeScale().setVisibleRange(preserveVisibleRange);
                console.log('Restored visible range:', preserveVisibleRange);
            } else {
                // Only fit content if no range to preserve (initial load)
                chart.timeScale().fitContent();
                volumeChart.timeScale().fitContent();
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

    // Reload gaps if enabled
    if (gapsEnabled) {
        await loadAndDisplayGaps();
    }

    // Reload engulfing patterns if enabled
    if (engulfingEnabled) {
        await loadAndDisplayEngulfing();
    }

    // Reload trend if enabled
    if (trendEnabled) {
        await loadAndDisplayTrend();
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
 * Toggle auto-refresh on/off
 */
function toggleAutoRefresh() {
    const button = document.getElementById('auto-refresh-toggle');

    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        button.textContent = 'Auto-Refresh: AUS';
        button.classList.remove('active');
        console.log('Auto-refresh disabled');
    } else {
        autoRefreshInterval = setInterval(async () => {
            console.log('Auto-refreshing data...');
            await loadChartData(currentTimeframe, CANDLE_LIMIT);

            // Reload active indicators
            const indicators = getActiveIndicators();
            for (const [indicator, checkbox] of Object.entries(indicators)) {
                if (checkbox.checked) {
                    await toggleIndicator(indicator, true);
                }
            }
        }, 60000); // Refresh every 60 seconds

        button.textContent = 'Auto-Refresh: AN';
        button.classList.add('active');
        console.log('Auto-refresh enabled (60s interval)');
    }
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

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', async () => {
        await loadChartData(currentTimeframe, CANDLE_LIMIT);

        // Reload active indicators
        const indicators = getActiveIndicators();
        for (const [indicator, checkbox] of Object.entries(indicators)) {
            if (checkbox.checked) {
                await toggleIndicator(indicator, true);
            }
        }
    });

    // Auto-refresh toggle
    document.getElementById('auto-refresh-toggle').addEventListener('click', () => {
        toggleAutoRefresh();
    });

    // Database update button
    document.getElementById('update-db-btn').addEventListener('click', async () => {
        await updateDatabase();
    });
}

/**
 * Update database from Binance (with confirmation)
 */
async function updateDatabase() {
    const button = document.getElementById('update-db-btn');
    const originalText = button.textContent;

    if (confirm('Neue Daten von Binance laden?\n\nDies kann 1-2 Minuten dauern.')) {
        try {
            button.disabled = true;
            button.textContent = '⏳ Lade Daten...';

            const response = await fetch('/api/update-database/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            const data = await response.json();

            if (data.success) {
                alert('✅ Datenbank erfolgreich aktualisiert!\n\nDie Seite wird neu geladen...');
                location.reload();
            } else {
                console.error('Update failed:', data);
                alert(`❌ Fehler beim Aktualisieren:\n\n${data.error || data.message}\n\nDetails in der Konsole (F12)`);
            }
        } catch (error) {
            console.error('Error updating database:', error);
            alert(`❌ Fehler beim Aktualisieren:\n\n${error.message}`);
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

/**
 * Update database from Binance silently (no confirmation, no reload popup)
 * Used internally by day analysis mode
 */
async function updateDatabaseSilent() {
    try {
        console.log('Fetching latest data from Binance...');

        const response = await fetch('/api/update-database/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (data.success) {
            console.log('✅ Database updated successfully');
            return true;
        } else {
            console.error('Database update failed:', data);
            return false;
        }
    } catch (error) {
        console.error('Error updating database silently:', error);
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

        console.log('Dashboard ready!');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        console.error('Error details:', error.message, error.stack);
        alert('Fehler beim Initialisieren des Dashboards\n\nDetails: ' + error.message + '\n\nBitte öffne die Browser-Konsole (F12) für weitere Informationen.');
    }
});

/**
 * Toggle gap visualization on/off
 */
async function toggleGaps() {
    gapsEnabled = !gapsEnabled;
    const button = document.getElementById('gaps-toggle');

    if (gapsEnabled) {
        button.classList.add('active');
        button.textContent = '📊 Gaps: AN';
        await loadAndDisplayGaps();
    } else {
        button.classList.remove('active');
        button.textContent = '📊 Gaps: AUS';
        clearGaps();
    }
}

/**
 * Toggle between regular gaps and Fair Value Gaps
 */
async function toggleGapType() {
    const button = document.getElementById('gap-type-toggle');

    if (gapType === 'regular') {
        gapType = 'fvg';
        button.textContent = 'FVG';
        button.title = 'Fair Value Gaps (ICT)';
    } else {
        gapType = 'regular';
        button.textContent = 'Regular';
        button.title = 'Standard Price Gaps';
    }

    // Reload gaps if currently enabled
    if (gapsEnabled) {
        clearGaps();
        await loadAndDisplayGaps();
    }
}

/**
 * Load gap data from API and display on chart
 */
async function loadAndDisplayGaps() {
    try {
        const limit = CANDLE_LIMIT;
        const response = await fetch(`/api/gaps/${currentTimeframe}/?gap_type=${gapType}&min_gap=0.1&limit=${limit}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log(`Loaded ${data.count} ${gapType} gaps for ${currentTimeframe}`);

        // Display gaps on chart
        displayGaps(data.gaps);

    } catch (error) {
        console.error('Error loading gaps:', error);
        alert(`Fehler beim Laden der Gaps:\n${error.message}`);
    }
}

/**
 * Display gaps as colored rectangles on the chart
 */
function displayGaps(gaps) {
    if (!chart || !gaps || gaps.length === 0) {
        console.log('No gaps to display');
        return;
    }

    clearGaps();

    gaps.forEach((gap) => {
        // Determine color based on gap type and filled status
        let color;
        if (gap.filled) {
            // Filled gaps: semi-transparent gray
            color = 'rgba(128, 128, 128, 0.15)';
        } else {
            // Unfilled gaps: colored by type
            if (gap.gap_type === 'bullish' || gap.gap_type === 'bullish_fvg') {
                color = 'rgba(38, 166, 154, 0.25)';  // Green/cyan
            } else {
                color = 'rgba(239, 83, 80, 0.25)';   // Red
            }
        }

        // Create price line series for the gap rectangle
        // Note: TradingView Lightweight Charts doesn't have native rectangle support
        // We'll use horizontal lines at the top and bottom of the gap
        const topLine = chart.addLineSeries({
            color: color.replace('0.25', '0.6'),
            lineWidth: 1,
            lineStyle: gap.filled ? 1 : 0,  // Dashed if filled, solid if not
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });

        const bottomLine = chart.addLineSeries({
            color: color.replace('0.25', '0.6'),
            lineWidth: 1,
            lineStyle: gap.filled ? 1 : 0,
            crosshairMarkerVisible: false,
            lastValueVisible: false,
            priceLineVisible: false,
        });

        // Set the horizontal lines
        topLine.setData([
            { time: gap.start_time, value: gap.gap_high },
            { time: gap.end_time + 3600, value: gap.gap_high }  // Extend a bit
        ]);

        bottomLine.setData([
            { time: gap.start_time, value: gap.gap_low },
            { time: gap.end_time + 3600, value: gap.gap_low }
        ]);

        // Store references for later removal
        gapSeries.push({ topLine, bottomLine, gap });
    });

    console.log(`Displayed ${gapSeries.length} gaps on chart`);
}

/**
 * Clear all gap visualizations from chart
 */
function clearGaps() {
    if (!chart) return;

    gapSeries.forEach(({ topLine, bottomLine }) => {
        try {
            chart.removeSeries(topLine);
            chart.removeSeries(bottomLine);
        } catch (error) {
            console.debug('Error removing gap series:', error);
        }
    });

    gapSeries = [];
    console.log('Cleared all gaps from chart');
}

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
 * Toggle trend analysis visualization on/off
 */
async function toggleTrend() {
    trendEnabled = !trendEnabled;
    const button = document.getElementById('trend-toggle');

    if (trendEnabled) {
        button.classList.add('active');
        button.textContent = '📈 Trend: AN';
        await loadAndDisplayTrend();
    } else {
        button.classList.remove('active');
        button.textContent = '📈 Trend: AUS';
        clearTrend();
    }
}

/**
 * Load trend data from API and display on chart
 */
async function loadAndDisplayTrend() {
    try {
        const limit = CANDLE_LIMIT;
        const lookback = 5;  // Default lookback window
        const minMove = 0.5;  // Minimum 0.5% move between swings

        const response = await fetch(
            `/api/trend/${currentTimeframe}/?lookback=${lookback}&min_move=${minMove}&limit=${limit}`
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log(`Trend detected: ${data.trend_type} (confidence: ${(data.confidence * 100).toFixed(1)}%)`);
        console.log(`Swing points: ${data.swing_points.length} (${data.statistics.swing_highs} highs, ${data.statistics.swing_lows} lows)`);

        // Store trend data
        trendData = data;

        // Display trendline and swing points
        displayTrendline(data);
        displaySwingPoints(data.swing_points);

    } catch (error) {
        console.error('Error loading trend:', error);
        alert(`Fehler beim Laden der Trend-Analyse:\n${error.message}`);
    }
}

/**
 * Display trendline on chart
 */
function displayTrendline(data) {
    if (!chart || !data.trendline_points || data.trendline_points.length < 2) {
        console.log('No trendline to display');
        return;
    }

    clearTrendline();

    // Determine color based on trend type
    let color;
    switch (data.trend_type) {
        case 'uptrend':
            color = '#26a69a';  // Green
            break;
        case 'downtrend':
            color = '#ef5350';  // Red
            break;
        default:
            color = '#888888';  // Gray for sideways
    }

    // Create line series for trendline
    trendLineSeries = chart.addLineSeries({
        color: color,
        lineWidth: 2,
        lineStyle: 0,  // Solid line
        crosshairMarkerVisible: true,
        lastValueVisible: true,
        priceLineVisible: false,
        title: `Trend: ${data.trend_type.toUpperCase()}`
    });

    // Set trendline data
    trendLineSeries.setData(data.trendline_points);

    console.log(`Displayed ${data.trend_type} trendline with ${data.trendline_points.length} points`);
}

/**
 * Display swing points as markers on chart
 */
function displaySwingPoints(swingPoints) {
    if (!candlestickSeries || !swingPoints || swingPoints.length === 0) {
        console.log('No swing points to display');
        return;
    }

    // Convert swing points to TradingView markers
    const markers = swingPoints.map(point => {
        const isHigh = point.type === 'high';

        return {
            time: point.time,
            position: isHigh ? 'aboveBar' : 'belowBar',
            color: isHigh ? '#ff9800' : '#2196f3',  // Orange for highs, blue for lows
            shape: 'circle',
            text: isHigh ? 'H' : 'L',
            size: 0.5  // Small markers
        };
    });

    // Get existing markers (e.g., engulfing patterns) and combine
    const existingMarkers = candlestickSeries.markers() || [];

    // Filter out old swing markers (H/L) but keep other markers
    const filteredExisting = existingMarkers.filter(m => m.text !== 'H' && m.text !== 'L');

    // Combine filtered existing with new swing markers
    const combinedMarkers = [...filteredExisting, ...markers];

    candlestickSeries.setMarkers(combinedMarkers);
    swingPointMarkers = swingPoints;

    console.log(`Displayed ${markers.length} swing point markers`);
}

/**
 * Clear trendline from chart
 */
function clearTrendline() {
    if (!chart || !trendLineSeries) return;

    try {
        chart.removeSeries(trendLineSeries);
    } catch (error) {
        console.debug('Error removing trendline series:', error);
    }

    trendLineSeries = null;
    console.log('Cleared trendline from chart');
}

/**
 * Clear all trend visualizations (trendline + swing markers)
 */
function clearTrend() {
    clearTrendline();

    // Remove swing point markers (keep other markers like engulfing)
    if (candlestickSeries && swingPointMarkers.length > 0) {
        const existingMarkers = candlestickSeries.markers() || [];
        const filteredMarkers = existingMarkers.filter(marker =>
            marker.text !== 'H' && marker.text !== 'L'
        );
        candlestickSeries.setMarkers(filteredMarkers);
    }

    swingPointMarkers = [];
    trendData = null;

    console.log('Cleared all trend visualizations');
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

        // Calculate time boundaries (current day start, yesterday start)
        const now = new Date();
        const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
        const yesterdayStart = new Date(todayStart);
        yesterdayStart.setDate(yesterdayStart.getDate() - 1);

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

        // Draw horizontal lines for previous day open/close
        drawPreviousDayLines(prevDayOpen, prevDayClose, todayStartUnix);

        // Set visible range to yesterday start → now
        const visibleFrom = yesterdayStartUnix;
        const visibleTo = Math.floor(now.getTime() / 1000);

        chart.timeScale().setVisibleRange({
            from: visibleFrom,
            to: visibleTo
        });

        volumeChart.timeScale().setVisibleRange({
            from: visibleFrom,
            to: visibleTo
        });

        console.log('Day analysis mode enabled');

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
 */
function disableDayAnalysis() {
    // Remove reference lines
    clearPreviousDayLines();

    // Restore original visible range
    if (savedVisibleRange && chart) {
        try {
            chart.timeScale().setVisibleRange(savedVisibleRange);
            volumeChart.timeScale().setVisibleRange(savedVisibleRange);
            console.log('Restored original visible range');
        } catch (error) {
            console.debug('Could not restore visible range, fitting content instead:', error);
            chart.timeScale().fitContent();
            volumeChart.timeScale().fitContent();
        }
        savedVisibleRange = null;
    } else if (chart) {
        // No saved range, just fit content
        chart.timeScale().fitContent();
        volumeChart.timeScale().fitContent();
    }

    console.log('Day analysis mode disabled');
}
