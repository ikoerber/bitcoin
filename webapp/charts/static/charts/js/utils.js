/**
 * Shared JavaScript Utilities
 *
 * Centralizes common patterns to eliminate code duplication:
 * - Fetch wrapper with error handling
 * - Loading state management
 * - DOM element visibility helpers
 */

/**
 * Fetch wrapper with standardized error handling
 *
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise<Object>} Parsed JSON response
 * @throws {Error} If fetch fails or response is not ok
 */
async function fetchJSON(url, options = {}) {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${url}:`, error);
        throw error;
    }
}

/**
 * Loading state manager for consistent UI feedback
 *
 * @param {Object} elements - DOM elements to manage
 * @param {HTMLElement} elements.loading - Loading message element
 * @param {HTMLElement} elements.content - Content container element
 * @param {HTMLElement} elements.error - Error message element
 * @param {HTMLElement} elements.noData - No data message element
 */
class LoadingStateManager {
    constructor(elements) {
        this.loading = elements.loading;
        this.content = elements.content;
        this.error = elements.error;
        this.noData = elements.noData;
    }

    /**
     * Show loading state, hide everything else
     */
    showLoading() {
        this.loading.style.display = 'block';
        this.content.style.display = 'none';
        this.error.style.display = 'none';
        this.noData.style.display = 'none';
    }

    /**
     * Show content, hide loading/error/noData
     */
    showContent() {
        this.loading.style.display = 'none';
        this.content.style.display = 'block';
        this.error.style.display = 'none';
        this.noData.style.display = 'none';
    }

    /**
     * Show error message, hide everything else
     */
    showError() {
        this.loading.style.display = 'none';
        this.content.style.display = 'none';
        this.error.style.display = 'block';
        this.noData.style.display = 'none';
    }

    /**
     * Show "no data" message, hide everything else
     */
    showNoData() {
        this.loading.style.display = 'none';
        this.content.style.display = 'none';
        this.error.style.display = 'none';
        this.noData.style.display = 'block';
    }
}

/**
 * Generic data fetcher with loading state management
 *
 * @param {string} url - API endpoint URL
 * @param {LoadingStateManager} stateManager - Loading state manager instance
 * @param {Function} renderCallback - Callback to render data
 * @param {string} moduleName - Module name for error logging
 * @returns {Promise<Object|null>} Fetched data or null on error
 */
async function fetchWithLoadingState(url, stateManager, renderCallback, moduleName = 'Module') {
    stateManager.showLoading();

    try {
        const data = await fetchJSON(url);

        // Check if data is empty
        const isEmpty = Array.isArray(data) ? data.length === 0 : !data;

        if (isEmpty) {
            stateManager.showNoData();
            return null;
        }

        // Render data
        if (renderCallback) {
            renderCallback(data);
        }

        stateManager.showContent();
        return data;

    } catch (error) {
        console.error(`[${moduleName}] Error fetching data:`, error);
        stateManager.showError();
        return null;
    }
}

/**
 * Format number with thousands separator
 *
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places (default: 2)
 * @returns {string} Formatted number
 */
function formatNumber(value, decimals = 2) {
    return value.toLocaleString('de-DE', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

/**
 * Format currency (EUR)
 *
 * @param {number} value - Amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(value) {
    return `€${formatNumber(value, 2)}`;
}

/**
 * Format percentage
 *
 * @param {number} value - Percentage value
 * @returns {string} Formatted percentage string
 */
function formatPercentage(value) {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${formatNumber(value, 2)}%`;
}

/**
 * Format datetime from timestamp
 *
 * @param {number} timestamp - Unix timestamp (seconds)
 * @returns {string} Formatted date string
 */
function formatDatetime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('de-DE', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format date only
 *
 * @param {number} timestamp - Unix timestamp (seconds)
 * @returns {string} Formatted date string
 */
function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('de-DE', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

/**
 * Debounce function execution
 *
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Show/hide element with animation
 *
 * @param {HTMLElement} element - Element to toggle
 * @param {boolean} show - True to show, false to hide
 */
function toggleElement(element, show) {
    element.style.display = show ? 'block' : 'none';
}

/**
 * Add CSS class if condition is true
 *
 * @param {HTMLElement} element - Target element
 * @param {string} className - CSS class name
 * @param {boolean} condition - Condition to check
 */
function toggleClass(element, className, condition) {
    if (condition) {
        element.classList.add(className);
    } else {
        element.classList.remove(className);
    }
}

/**
 * Safe querySelector that throws descriptive error
 *
 * @param {string} selector - CSS selector
 * @param {HTMLElement} parent - Parent element (default: document)
 * @returns {HTMLElement} Found element
 * @throws {Error} If element not found
 */
function requireElement(selector, parent = document) {
    const element = parent.querySelector(selector);
    if (!element) {
        throw new Error(`Required element not found: ${selector}`);
    }
    return element;
}

/**
 * Build URL with query parameters
 *
 * @param {string} baseUrl - Base URL
 * @param {Object} params - Query parameters
 * @returns {string} Complete URL with query string
 */
function buildUrl(baseUrl, params = {}) {
    const url = new URL(baseUrl, window.location.origin);
    Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined) {
            url.searchParams.append(key, params[key]);
        }
    });
    return url.toString();
}
