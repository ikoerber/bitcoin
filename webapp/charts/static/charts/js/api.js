/**
 * API Interaction Layer for Bitcoin Trading Dashboard
 *
 * Provides async functions for fetching data from Django REST API endpoints.
 * Uses shared fetchJSON wrapper from utils.js to eliminate code duplication.
 */

const API = {
    baseURL: '',  // Same domain, no need for full URL

    /**
     * Fetch OHLCV candlestick data for a timeframe
     *
     * @param {string} timeframe - Timeframe ('15m', '1h', '4h', '1d')
     * @param {number} limit - Maximum number of candles (default: 500)
     * @returns {Promise<Object>} OHLCV data response
     */
    async fetchOHLCV(timeframe, limit = 500) {
        const url = buildUrl(`/api/ohlcv/${timeframe}/`, { limit });
        return fetchJSON(url);
    },

    /**
     * Fetch latest price for a timeframe
     *
     * @param {string} timeframe - Timeframe ('15m', '1h', '4h', '1d')
     * @returns {Promise<Object>} Latest price data
     */
    async fetchLatestPrice(timeframe) {
        const url = `/api/latest-price/${timeframe}/`;
        return fetchJSON(url);
    },

    /**
     * Fetch technical indicator data
     *
     * @param {string} timeframe - Timeframe ('15m', '1h', '4h', '1d')
     * @param {string} indicator - Indicator type ('rsi', 'sma', 'ema', 'bb')
     * @param {number} period - Indicator period (default: 14 for RSI, 20 for others)
     * @param {number} limit - Maximum number of data points (default: 500)
     * @returns {Promise<Object>} Indicator data response
     */
    async fetchIndicator(timeframe, indicator, period = null, limit = 500) {
        // Default periods
        if (period === null) {
            period = indicator === 'rsi' ? 14 : 20;
        }

        const url = buildUrl(`/api/indicators/${timeframe}/`, {
            indicator,
            period,
            limit
        });
        return fetchJSON(url);
    },

    /**
     * Fetch database summary for all timeframes
     *
     * @returns {Promise<Object>} Summary statistics
     */
    async fetchSummary() {
        return fetchJSON('/api/summary/');
    },

    /**
     * Fetch auto-update scheduler status
     *
     * @returns {Promise<Object>} Scheduler status with next run times
     */
    async fetchAutoUpdateStatus() {
        return fetchJSON('/api/auto-update-status/');
    }
};
