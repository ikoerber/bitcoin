/**
 * Cashflow Timeline JavaScript
 *
 * Handles:
 * - Fetching transactions from API
 * - Rendering timeline entries
 * - Filtering and sorting
 * - Summary statistics
 */

// State
let currentTransactions = [];
let currentDays = 30;
let currentTypeFilter = '';

// DOM Elements
const timelineElement = document.getElementById('timeline');
const loadingMessage = document.getElementById('loading-message');
const errorMessage = document.getElementById('error-message');
const noDataMessage = document.getElementById('no-data-message');
const daysSelect = document.getElementById('days-select');
const typeFilter = document.getElementById('type-filter');
const refreshBtn = document.getElementById('refresh-btn');

// Summary elements
const totalTransactionsEl = document.getElementById('total-transactions');
const totalDepositsEl = document.getElementById('total-deposits');
const totalBuysEl = document.getElementById('total-buys');
const totalSellsEl = document.getElementById('total-sells');

/**
 * Initialize the page
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Cashflow] Initializing cashflow timeline');

    // Event listeners
    daysSelect.addEventListener('change', (e) => {
        currentDays = parseInt(e.target.value);
        loadTransactions();
    });

    typeFilter.addEventListener('change', (e) => {
        currentTypeFilter = e.target.value;
        loadTransactions();
    });

    refreshBtn.addEventListener('click', () => {
        loadTransactions();
    });

    // Initial load
    loadTransactions();
});

/**
 * Load transactions from API
 */
async function loadTransactions() {
    console.log(`[Cashflow] Loading transactions: days=${currentDays}, type=${currentTypeFilter || 'all'}`);

    // Show loading
    loadingMessage.style.display = 'block';
    timelineElement.style.display = 'none';
    errorMessage.style.display = 'none';
    noDataMessage.style.display = 'none';

    try {
        // Build API URL
        const params = new URLSearchParams({
            days: currentDays,
            limit: 1000
        });

        if (currentTypeFilter) {
            params.append('type', currentTypeFilter);
        }

        const url = `/api/cashflow/?${params.toString()}`;
        console.log(`[Cashflow] Fetching: ${url}`);

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        console.log(`[Cashflow] Received ${data.transactions.length} transactions`);

        currentTransactions = data.transactions;

        // Hide loading
        loadingMessage.style.display = 'none';

        if (currentTransactions.length === 0) {
            noDataMessage.style.display = 'block';
        } else {
            timelineElement.style.display = 'block';
            renderTimeline();
            updateSummary();
        }

    } catch (error) {
        console.error('[Cashflow] Error loading transactions:', error);
        loadingMessage.style.display = 'none';
        errorMessage.style.display = 'block';
        errorMessage.querySelector('p').textContent = `Fehler beim Laden: ${error.message}`;
    }
}

/**
 * Render timeline entries
 */
function renderTimeline() {
    console.log(`[Cashflow] Rendering ${currentTransactions.length} timeline entries`);

    timelineElement.innerHTML = '';

    currentTransactions.forEach(tx => {
        const entry = createTimelineEntry(tx);
        timelineElement.appendChild(entry);
    });
}

/**
 * Create a timeline entry element
 */
function createTimelineEntry(tx) {
    const entry = document.createElement('div');
    entry.className = `timeline-entry type-${tx.type} status-${tx.status}`;

    // Header
    const header = document.createElement('div');
    header.className = 'entry-header';

    const typeLabel = document.createElement('span');
    typeLabel.className = `entry-type type-${tx.type}`;
    typeLabel.textContent = getTypeLabel(tx.type);

    const datetime = document.createElement('span');
    datetime.className = 'entry-datetime';
    datetime.textContent = formatDateTime(tx.datetime);

    header.appendChild(typeLabel);
    header.appendChild(datetime);

    // Content
    const content = document.createElement('div');
    content.className = 'entry-content';

    const description = document.createElement('div');
    description.className = 'entry-description';
    description.textContent = tx.description;

    const amount = document.createElement('div');
    amount.className = `entry-amount ${getAmountClass(tx.amount)}`;
    amount.textContent = formatAmount(tx.amount, tx.currency);

    content.appendChild(description);
    content.appendChild(amount);

    // Details
    const details = document.createElement('div');
    details.className = 'entry-details';

    // Add relevant details based on transaction type
    if (tx.price !== null) {
        addDetail(details, 'Preis', `€${tx.price.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`);
    }

    if (tx.amount_btc !== undefined) {
        addDetail(details, 'BTC Menge', `${tx.amount_btc.toFixed(8)} BTC`);
    }

    if (tx.from_currency && tx.to_currency) {
        addDetail(details, 'Conversion', `${tx.from_amount.toFixed(8)} ${tx.from_currency} → ${tx.to_amount.toFixed(8)} ${tx.to_currency}`);
    }

    if (tx.fee > 0) {
        addDetail(details, 'Gebühr', `${tx.fee.toFixed(8)} ${tx.fee_currency}`);
    }

    // Status badge
    const statusBadge = document.createElement('span');
    statusBadge.className = `status-badge status-${tx.status}`;
    statusBadge.textContent = getStatusLabel(tx.status);
    addDetail(details, 'Status', statusBadge.outerHTML);

    // Assemble entry
    entry.appendChild(header);
    entry.appendChild(content);
    if (details.children.length > 0) {
        entry.appendChild(details);
    }

    return entry;
}

/**
 * Add a detail row
 */
function addDetail(detailsElement, label, value) {
    const item = document.createElement('div');
    item.className = 'detail-item';

    const labelEl = document.createElement('span');
    labelEl.className = 'detail-label';
    labelEl.textContent = label + ':';

    const valueEl = document.createElement('span');
    valueEl.className = 'detail-value';

    if (typeof value === 'string' && value.startsWith('<')) {
        valueEl.innerHTML = value;
    } else {
        valueEl.textContent = value;
    }

    item.appendChild(labelEl);
    item.appendChild(valueEl);
    detailsElement.appendChild(item);
}

/**
 * Update summary statistics
 */
function updateSummary() {
    const stats = {
        total: currentTransactions.length,
        deposits: 0,
        depositAmount: 0,
        buys: 0,
        buyAmount: 0,
        sells: 0,
        sellAmount: 0
    };

    currentTransactions.forEach(tx => {
        if (tx.type === 'deposit') {
            stats.deposits++;
            stats.depositAmount += tx.amount;
        } else if (tx.type === 'buy') {
            stats.buys++;
            stats.buyAmount += tx.amount_btc || 0;
        } else if (tx.type === 'sell') {
            stats.sells++;
            stats.sellAmount += tx.amount_btc || 0;
        }
    });

    totalTransactionsEl.textContent = stats.total;
    totalDepositsEl.textContent = `€${stats.depositAmount.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})} (${stats.deposits})`;
    totalBuysEl.textContent = `${stats.buyAmount.toFixed(8)} BTC (${stats.buys})`;
    totalSellsEl.textContent = `${stats.sellAmount.toFixed(8)} BTC (${stats.sells})`;

    console.log('[Cashflow] Summary updated:', stats);
}

/**
 * Get human-readable type label
 */
function getTypeLabel(type) {
    const labels = {
        'deposit': 'Einzahlung',
        'withdrawal': 'Auszahlung',
        'buy': 'Kauf',
        'sell': 'Verkauf',
        'convert': 'Conversion',
        'transfer': 'Transfer',
        'limit_buy': 'Limit Buy',
        'limit_sell': 'Limit Sell'
    };
    return labels[type] || type;
}

/**
 * Get status label
 */
function getStatusLabel(status) {
    const labels = {
        'completed': 'Abgeschlossen',
        'open': 'Offen',
        'pending': 'Ausstehend',
        'success': 'Erfolgreich'
    };
    return labels[status] || status;
}

/**
 * Get amount CSS class
 */
function getAmountClass(amount) {
    if (amount > 0) return 'positive';
    if (amount < 0) return 'negative';
    return 'neutral';
}

/**
 * Format amount with currency
 */
function formatAmount(amount, currency) {
    const absAmount = Math.abs(amount);
    const sign = amount >= 0 ? '+' : '-';

    if (currency === 'EUR') {
        return `${sign}€${absAmount.toLocaleString('de-DE', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    } else if (currency === 'BTC') {
        return `${sign}${absAmount.toFixed(8)} BTC`;
    } else if (currency === 'BNB') {
        return `${sign}${absAmount.toFixed(8)} BNB`;
    } else {
        return `${sign}${absAmount} ${currency}`;
    }
}

/**
 * Format datetime
 */
function formatDateTime(datetimeStr) {
    const date = new Date(datetimeStr);
    return date.toLocaleString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
