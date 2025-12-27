/**
 * Technical Indicators Manager
 *
 * Manages adding and removing technical indicators on the TradingView chart.
 */

const IndicatorManager = {
    activeSeries: {},

    /**
     * Add RSI (Relative Strength Index) indicator to chart
     *
     * @param {Object} chart - TradingView chart instance
     * @param {string} timeframe - Current timeframe
     */
    async addRSI(chart, timeframe) {
        try {
            const data = await API.fetchIndicator(timeframe, 'rsi', 14);

            // Remove existing RSI series if present
            if (this.activeSeries.rsi) {
                chart.removeSeries(this.activeSeries.rsi);
            }

            // Add RSI line series
            const series = chart.addLineSeries({
                color: '#ff9800',
                lineWidth: 2,
                priceScaleId: 'rsi',
                title: 'RSI (14)',
            });

            series.setData(data.data);

            // Configure RSI price scale (0-100 range)
            chart.priceScale('rsi').applyOptions({
                scaleMargins: {
                    top: 0.8,
                    bottom: 0,
                },
            });

            this.activeSeries.rsi = series;
            console.log('RSI indicator added');
        } catch (error) {
            console.error('Failed to add RSI indicator:', error);
            alert('Fehler beim Laden des RSI-Indikators');
        }
    },

    /**
     * Add SMA (Simple Moving Average) indicator to chart
     *
     * @param {Object} chart - TradingView chart instance
     * @param {string} timeframe - Current timeframe
     */
    async addSMA(chart, timeframe) {
        try {
            const data = await API.fetchIndicator(timeframe, 'sma', 20);

            // Remove existing SMA series if present
            if (this.activeSeries.sma) {
                chart.removeSeries(this.activeSeries.sma);
            }

            // Add SMA line series
            const series = chart.addLineSeries({
                color: '#2196f3',
                lineWidth: 2,
                title: 'SMA (20)',
            });

            series.setData(data.data);
            this.activeSeries.sma = series;
            console.log('SMA indicator added');
        } catch (error) {
            console.error('Failed to add SMA indicator:', error);
            alert('Fehler beim Laden des SMA-Indikators');
        }
    },

    /**
     * Add EMA (Exponential Moving Average) indicator to chart
     *
     * @param {Object} chart - TradingView chart instance
     * @param {string} timeframe - Current timeframe
     */
    async addEMA(chart, timeframe) {
        try {
            const data = await API.fetchIndicator(timeframe, 'ema', 20);

            // Remove existing EMA series if present
            if (this.activeSeries.ema) {
                chart.removeSeries(this.activeSeries.ema);
            }

            // Add EMA line series
            const series = chart.addLineSeries({
                color: '#9c27b0',
                lineWidth: 2,
                title: 'EMA (20)',
            });

            series.setData(data.data);
            this.activeSeries.ema = series;
            console.log('EMA indicator added');
        } catch (error) {
            console.error('Failed to add EMA indicator:', error);
            alert('Fehler beim Laden des EMA-Indikators');
        }
    },

    /**
     * Add Bollinger Bands indicator to chart
     *
     * @param {Object} chart - TradingView chart instance
     * @param {string} timeframe - Current timeframe
     */
    async addBollingerBands(chart, timeframe) {
        try {
            const data = await API.fetchIndicator(timeframe, 'bb', 20);

            // Remove existing Bollinger Bands series if present
            ['bb_upper', 'bb_middle', 'bb_lower'].forEach(key => {
                if (this.activeSeries[key]) {
                    chart.removeSeries(this.activeSeries[key]);
                }
            });

            // Add upper band
            const upperSeries = chart.addLineSeries({
                color: 'rgba(33, 150, 243, 0.5)',
                lineWidth: 1,
                title: 'BB Upper',
            });
            upperSeries.setData(data.data.map(d => ({ time: d.time, value: d.upper })));
            this.activeSeries.bb_upper = upperSeries;

            // Add middle band
            const middleSeries = chart.addLineSeries({
                color: '#2196f3',
                lineWidth: 1,
                title: 'BB Middle',
            });
            middleSeries.setData(data.data.map(d => ({ time: d.time, value: d.middle })));
            this.activeSeries.bb_middle = middleSeries;

            // Add lower band
            const lowerSeries = chart.addLineSeries({
                color: 'rgba(33, 150, 243, 0.5)',
                lineWidth: 1,
                title: 'BB Lower',
            });
            lowerSeries.setData(data.data.map(d => ({ time: d.time, value: d.lower })));
            this.activeSeries.bb_lower = lowerSeries;

            console.log('Bollinger Bands indicator added');
        } catch (error) {
            console.error('Failed to add Bollinger Bands indicator:', error);
            alert('Fehler beim Laden der Bollinger Bands');
        }
    },

    /**
     * Remove indicator from chart
     *
     * @param {Object} chart - TradingView chart instance
     * @param {string} indicator - Indicator type ('rsi', 'sma', 'ema', 'bb')
     */
    removeIndicator(chart, indicator) {
        if (indicator === 'bb') {
            // Remove all three Bollinger Bands lines
            ['bb_upper', 'bb_middle', 'bb_lower'].forEach(key => {
                if (this.activeSeries[key]) {
                    chart.removeSeries(this.activeSeries[key]);
                    delete this.activeSeries[key];
                }
            });
            console.log('Bollinger Bands removed');
        } else {
            // Remove single indicator
            if (this.activeSeries[indicator]) {
                chart.removeSeries(this.activeSeries[indicator]);
                delete this.activeSeries[indicator];
                console.log(`${indicator.toUpperCase()} indicator removed`);
            }
        }
    }
};
