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

    // Add candlestick series
    candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderUpColor: '#26a69a',
        borderDownColor: '#ef5350',
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
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
 */
async function loadChartData(timeframe, limit = 1000) {
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

        // Fit content to visible area
        try {
            chart.timeScale().fitContent();
            volumeChart.timeScale().fitContent();
        } catch (error) {
            console.warn('Could not fit content:', error.message);
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
    const limitElement = document.getElementById('candle-limit');
    const limit = parseInt(limitElement.value);

    // Show if we hit the limit
    const limitInfo = response.count >= limit ? ` (max ${limit})` : '';
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
    const limit = parseInt(document.getElementById('candle-limit').value);
    await loadChartData(timeframe, limit);

    // Reload active indicators
    const indicators = getActiveIndicators();
    for (const [indicator, checkbox] of Object.entries(indicators)) {
        if (checkbox.checked) {
            await toggleIndicator(indicator, true);
        }
    }
}

/**
 * Handle candle limit change event
 */
async function onCandleLimitChange() {
    const limit = parseInt(document.getElementById('candle-limit').value);
    await loadChartData(currentTimeframe, limit);

    // Reload active indicators
    const indicators = getActiveIndicators();
    for (const [indicator, checkbox] of Object.entries(indicators)) {
        if (checkbox.checked) {
            await toggleIndicator(indicator, true);
        }
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
            await loadChartData(currentTimeframe);

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

    // Candle limit selector
    document.getElementById('candle-limit').addEventListener('change', () => {
        onCandleLimitChange();
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
        await loadChartData(currentTimeframe);

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
 * Update database from Binance
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
 * Initialize dashboard on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Bitcoin Trading Dashboard initializing...');

    try {
        console.log('Step 1: Initializing charts...');
        initChart();

        console.log('Step 2: Initializing event listeners...');
        initEventListeners();

        console.log('Step 3: Loading chart data for timeframe:', currentTimeframe);
        await loadChartData(currentTimeframe);

        console.log('Dashboard ready!');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        console.error('Error details:', error.message, error.stack);
        alert('Fehler beim Initialisieren des Dashboards\n\nDetails: ' + error.message + '\n\nBitte öffne die Browser-Konsole (F12) für weitere Informationen.');
    }
});
