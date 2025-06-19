// DOM helper utilities
export function createElement(tag, className, innerHTML = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (innerHTML) element.innerHTML = innerHTML;
    return element;
}

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

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
}

export function updateIcons() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}