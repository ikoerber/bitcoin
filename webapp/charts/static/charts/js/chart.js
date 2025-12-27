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
        borderVisible: false,
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
        const timeRange = chart.timeScale().getVisibleRange();
        if (timeRange) {
            volumeChart.timeScale().setVisibleRange(timeRange);
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
async function loadChartData(timeframe) {
    showLoading();

    try {
        // Fetch OHLCV data
        const response = await API.fetchOHLCV(timeframe, 1000);

        if (!response.data || response.data.length === 0) {
            alert('Keine Daten verfügbar für diesen Zeitrahmen');
            hideLoading();
            return;
        }

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
        chart.timeScale().fitContent();
        volumeChart.timeScale().fitContent();

        hideLoading();
        console.log(`Loaded ${response.count} candles for ${timeframe}`);
    } catch (error) {
        console.error('Error loading chart data:', error);
        hideLoading();
        alert('Fehler beim Laden der Chart-Daten. Bitte versuche es erneut.');
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
    document.getElementById('candle-count').textContent = response.count.toLocaleString('de-DE');

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
    await loadChartData(timeframe);

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
}

/**
 * Initialize dashboard on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Bitcoin Trading Dashboard initializing...');

    try {
        initChart();
        initEventListeners();
        await loadChartData(currentTimeframe);

        console.log('Dashboard ready!');
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        alert('Fehler beim Initialisieren des Dashboards');
    }
});
