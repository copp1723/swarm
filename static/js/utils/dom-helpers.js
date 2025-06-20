// @ts-check
// DOM helper utilities

/**
 * Create DOM element with optional class and innerHTML
 * Follows Core Development Rules for DRY enforcement and utility extraction
 * @param {string} tag - HTML tag name to create
 * @param {string} className - CSS class names to apply
 * @param {string} innerHTML - Inner HTML content to set
 * @returns {HTMLElement} Created DOM element
 */
export function createElement(tag, className, innerHTML = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (innerHTML) element.innerHTML = innerHTML;
    return element;
}

/**
 * Escape HTML to prevent XSS attacks
 * Implements Core Development Rules for input sanitization
 * @param {string} text - Text to escape
 * @returns {string} HTML-escaped text
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show notification with automatic dismiss and type-based styling
 * Implements Core Development Rules for user feedback and visual states
 * @param {string} message - Notification message to display
 * @param {'info'|'success'|'warning'|'error'} type - Notification type for styling
 * @returns {HTMLElement} Created notification element
 */
export function showNotification(message, type = 'info') {
    const typeClasses = {
        error: 'bg-red-500 text-white',
        success: 'bg-green-500 text-white',
        warning: 'bg-yellow-500 text-white',
        info: 'bg-blue-500 text-white'
    };

    const notification = createElement('div', 
        `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 animate-slide-in ${typeClasses[type] || typeClasses.info}`
    );
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
    
    return notification;
}

/**
 * Update all Lucide icons in the document
 * Ensures icons are properly rendered after dynamic content changes
 * @returns {void}
 */
export function updateIcons() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

/**
 * Debounce function for performance optimization
 * Implements Core Development Rules for performance requirements and memory monitoring
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(func, wait) {
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
 * Throttle function for performance optimization
 * Implements Core Development Rules for performance requirements
 * @param {Function} func - Function to throttle
 * @param {number} limit - Throttle limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}
//# sourceMappingURL=dom-helpers.js.map
