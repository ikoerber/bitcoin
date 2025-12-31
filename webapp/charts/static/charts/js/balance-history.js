/**
 * Balance History JavaScript
 *
 * Handles:
 * - Fetching daily balance data from API
 * - Rendering Chart.js charts (total value + individual assets)
 * - Rendering balance table
 * - Time period filtering
 */

// State
let currentDays = 30;
let balanceData = null;
let totalChart = null;
let assetsChart = null;
let sankeyChart = null;

// DOM Elements
const loadingMessage = document.getElementById('loading-message');
const errorMessage = document.getElementById('error-message');
const noDataMessage = document.getElementById('no-data-message');
const chartsContainer = document.getElementById('charts-container');
const daysSelect = document.getElementById('days-select');
const refreshBtn = document.getElementById('refresh-btn');

// Summary elements
const totalValueEl = document.getElementById('total-value');
const eurBalanceEl = document.getElementById('eur-balance');
const btcBalanceEl = document.getElementById('btc-balance');
const bnbBalanceEl = document.getElementById('bnb-balance');

// Chart elements
const totalChartCanvas = document.getElementById('total-chart');
const assetsChartCanvas = document.getElementById('assets-chart');
const sankeyChartCanvas = document.getElementById('sankey-chart');
const balanceTableBody = document.getElementById('balance-table-body');

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('[BalanceHistory] Initializing balance history view');

    // Event listeners
    daysSelect.addEventListener('change', (e) => {
        currentDays = parseInt(e.target.value);
        loadBalanceHistory();
    });

    refreshBtn.addEventListener('click', () => {
        loadBalanceHistory();
    });

    // Initial load
    loadBalanceHistory();
});

/**
 * Load balance history from API
 */
async function loadBalanceHistory() {
    console.log(`[BalanceHistory] Loading balance history: days=${currentDays}`);

    // Show loading
    loadingMessage.style.display = 'block';
    chartsContainer.style.display = 'none';
    errorMessage.style.display = 'none';
    noDataMessage.style.display = 'none';

    try {
        // Build API URL
        const url = `/api/balance-history/?days=${currentDays}`;
        console.log(`[BalanceHistory] Fetching: ${url}`);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        balanceData = await response.json();
        console.log(`[BalanceHistory] Received ${balanceData.dates.length} days of data`);

        // Hide loading
        loadingMessage.style.display = 'none';

        if (balanceData.dates.length === 0) {
            noDataMessage.style.display = 'block';
        } else {
            chartsContainer.style.display = 'block';
            updateSummary();
            renderCharts();
            renderTable();
        }

    } catch (error) {
        console.error('[BalanceHistory] Error loading balance history:', error);
        loadingMessage.style.display = 'none';
        errorMessage.style.display = 'block';
        errorMessage.querySelector('p').textContent = `Fehler beim Laden: ${error.message}`;
    }
}

/**
 * Update summary cards
 */
function updateSummary() {
    const lastIndex = balanceData.dates.length - 1;

    const totalValue = balanceData.total_value_eur[lastIndex];
    const eurValue = balanceData.eur_balance[lastIndex];
    const btcValue = balanceData.btc_value_eur[lastIndex];
    const bnbValue = balanceData.bnb_value_eur[lastIndex];

    totalValueEl.textContent = `€${totalValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    eurBalanceEl.textContent = `€${eurValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    btcBalanceEl.textContent = `€${btcValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    bnbBalanceEl.textContent = `€${bnbValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    console.log('[BalanceHistory] Summary updated:', { totalValue, eurValue, btcValue, bnbValue });
}

/**
 * Render Chart.js charts
 */
function renderCharts() {
    // Destroy existing charts
    if (totalChart) {
        totalChart.destroy();
    }
    if (assetsChart) {
        assetsChart.destroy();
    }
    if (sankeyChart) {
        sankeyChart.destroy();
    }

    // Format dates for display
    const labels = balanceData.dates.map(date => {
        const d = new Date(date);
        return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
    });

    // Chart.js common options
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    color: '#d1d4dc',
                    font: { size: 12 }
                }
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: '#131722',
                titleColor: '#d1d4dc',
                bodyColor: '#d1d4dc',
                borderColor: '#2a2e39',
                borderWidth: 1
            }
        },
        scales: {
            x: {
                grid: { color: '#2a2e39' },
                ticks: { color: '#9598a1' }
            },
            y: {
                grid: { color: '#2a2e39' },
                ticks: {
                    color: '#9598a1',
                    callback: function(value) {
                        return '€' + value.toLocaleString('de-DE');
                    }
                }
            }
        }
    };

    // 1. Total Value Chart
    totalChart = new Chart(totalChartCanvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Gesamtvermögen (EUR)',
                data: balanceData.total_value_eur,
                borderColor: '#2962ff',
                backgroundColor: 'rgba(41, 98, 255, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointHoverRadius: 5
            }]
        },
        options: {
            ...commonOptions,
            plugins: {
                ...commonOptions.plugins,
                title: {
                    display: false
                }
            }
        }
    });

    // 2. Stacked Bar Chart - Assets Composition
    assetsChart = new Chart(assetsChartCanvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'EUR Balance',
                    data: balanceData.eur_balance,
                    backgroundColor: '#4caf50',
                    borderColor: '#4caf50',
                    borderWidth: 1
                },
                {
                    label: 'BTC Wert (EUR)',
                    data: balanceData.btc_value_eur,
                    backgroundColor: '#ff9800',
                    borderColor: '#ff9800',
                    borderWidth: 1
                },
                {
                    label: 'BNB Wert (EUR)',
                    data: balanceData.bnb_value_eur,
                    backgroundColor: '#9c27b0',
                    borderColor: '#9c27b0',
                    borderWidth: 1
                }
            ]
        },
        options: {
            ...commonOptions,
            scales: {
                x: {
                    stacked: true,
                    grid: { color: '#2a2e39' },
                    ticks: { color: '#9598a1' }
                },
                y: {
                    stacked: true,
                    grid: { color: '#2a2e39' },
                    ticks: {
                        color: '#9598a1',
                        callback: function(value) {
                            return '€' + value.toLocaleString('de-DE');
                        }
                    }
                }
            },
            plugins: {
                ...commonOptions.plugins,
                title: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#131722',
                    titleColor: '#d1d4dc',
                    bodyColor: '#d1d4dc',
                    borderColor: '#2a2e39',
                    borderWidth: 1,
                    callbacks: {
                        footer: function(tooltipItems) {
                            let total = 0;
                            tooltipItems.forEach(item => {
                                total += item.parsed.y;
                            });
                            return 'Gesamt: €' + total.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                        }
                    }
                }
            }
        }
    });

    // 3. Sankey Diagram - Money Flows
    if (balanceData.flows) {
        const flows = balanceData.flows;
        const sankeyData = [];

        // Build Sankey data structure: [{from, to, flow}]
        if (flows.deposits_to_eur > 0) {
            sankeyData.push({from: 'Einzahlungen', to: 'EUR Balance', flow: flows.deposits_to_eur});
        }
        if (flows.eur_to_btc > 0) {
            sankeyData.push({from: 'EUR Balance', to: 'BTC Käufe', flow: flows.eur_to_btc});
        }
        if (flows.btc_to_eur > 0) {
            sankeyData.push({from: 'BTC Verkäufe', to: 'EUR Balance', flow: flows.btc_to_eur});
        }
        if (flows.eur_to_bnb > 0) {
            sankeyData.push({from: 'EUR Balance', to: 'BNB Converts', flow: flows.eur_to_bnb});
        }
        if (flows.bnb_to_fees > 0) {
            sankeyData.push({from: 'BNB Balance', to: 'Handelsgebühren', flow: flows.bnb_to_fees});
        }
        if (flows.eur_to_withdrawals > 0) {
            sankeyData.push({from: 'EUR Balance', to: 'Auszahlungen', flow: flows.eur_to_withdrawals});
        }

        sankeyChart = new Chart(sankeyChartCanvas, {
            type: 'sankey',
            data: {
                datasets: [{
                    data: sankeyData,
                    colorFrom: (c) => {
                        // Color based on source node
                        const from = c.dataset.data[c.dataIndex].from;
                        if (from.includes('Einzahlung')) return 'rgba(76, 175, 80, 0.7)';
                        if (from.includes('EUR')) return 'rgba(33, 150, 243, 0.7)';
                        if (from.includes('BTC')) return 'rgba(255, 152, 0, 0.7)';
                        if (from.includes('BNB')) return 'rgba(156, 39, 176, 0.7)';
                        return 'rgba(100, 100, 100, 0.7)';
                    },
                    colorTo: (c) => {
                        // Color based on target node
                        const to = c.dataset.data[c.dataIndex].to;
                        if (to.includes('EUR')) return 'rgba(33, 150, 243, 0.7)';
                        if (to.includes('BTC')) return 'rgba(255, 152, 0, 0.7)';
                        if (to.includes('BNB')) return 'rgba(156, 39, 176, 0.7)';
                        if (to.includes('Gebühr')) return 'rgba(244, 67, 54, 0.7)';
                        if (to.includes('Auszahlung')) return 'rgba(244, 67, 54, 0.7)';
                        return 'rgba(100, 100, 100, 0.7)';
                    },
                    colorMode: 'gradient',
                    labels: {
                        color: '#d1d4dc',
                        font: { size: 12 }
                    }
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: '#131722',
                        titleColor: '#d1d4dc',
                        bodyColor: '#d1d4dc',
                        borderColor: '#2a2e39',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                const flow = context.raw;
                                return `${flow.from} → ${flow.to}: €${flow.flow.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                            }
                        }
                    }
                }
            }
        });

        console.log('[BalanceHistory] Sankey chart rendered with', sankeyData.length, 'flows');
    }

    console.log('[BalanceHistory] Charts rendered');
}

/**
 * Render balance table
 */
function renderTable() {
    balanceTableBody.innerHTML = '';

    // Reverse order to show newest first
    const indices = Array.from({ length: balanceData.dates.length }, (_, i) => i).reverse();

    indices.forEach(i => {
        const row = document.createElement('tr');

        const date = new Date(balanceData.dates[i]);
        const dateStr = date.toLocaleDateString('de-DE', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });

        const eurBal = balanceData.eur_balance[i];
        const btcBal = balanceData.btc_balance[i];
        const btcValue = balanceData.btc_value_eur[i];
        const bnbBal = balanceData.bnb_balance[i];
        const bnbValue = balanceData.bnb_value_eur[i];
        const totalValue = balanceData.total_value_eur[i];

        row.innerHTML = `
            <td>${dateStr}</td>
            <td>€${eurBal.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${btcBal.toFixed(8)} BTC</td>
            <td>€${btcValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td>${bnbBal.toFixed(8)} BNB</td>
            <td>€${bnbValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td class="value-total">€${totalValue.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
        `;

        balanceTableBody.appendChild(row);
    });

    console.log(`[BalanceHistory] Table rendered with ${indices.length} rows`);
}
