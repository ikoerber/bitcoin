/**
 * API Interaction Layer for Bitcoin Trading Dashboard
 *
 * Provides async functions for fetching data from Django REST API endpoints.
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
        const url = `/api/ohlcv/${timeframe}/?limit=${limit}`;

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error fetching OHLCV data for ${timeframe}:`, error);
            throw error;
        }
    },

    /**
     * Fetch latest price for a timeframe
     *
     * @param {string} timeframe - Timeframe ('15m', '1h', '4h', '1d')
     * @returns {Promise<Object>} Latest price data
     */
    async fetchLatestPrice(timeframe) {
        const url = `/api/latest-price/${timeframe}/`;

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error fetching latest price for ${timeframe}:`, error);
            throw error;
        }
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

        const url = `/api/indicators/${timeframe}/?indicator=${indicator}&period=${period}&limit=${limit}`;

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${indicator} indicator for ${timeframe}:`, error);
            throw error;
        }
    },

    /**
     * Fetch database summary for all timeframes
     *
     * @returns {Promise<Object>} Summary statistics
     */
    async fetchSummary() {
        const url = `/api/summary/`;

        try {
            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching database summary:', error);
            throw error;
        }
    }
};
