// UX Enhancement JavaScript - Improved accessibility and keyboard navigation

// Initialize UX enhancements when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add skip navigation link
    addSkipNavigation();
    
    // Initialize keyboard shortcuts
    initializeKeyboardShortcuts();
    
    // Add ARIA labels and roles
    enhanceAccessibility();
    
    // Initialize theme toggle
    initializeThemeToggle();
    
    // Add loading state handlers
    initializeLoadingStates();
    
    // Enhance focus management
    enhanceFocusManagement();
    
    // Add quick actions
    addQuickActions();
    
    // Initialize tooltips
    initializeTooltips();
});

// Add skip navigation link
function addSkipNavigation() {
    const skipNav = document.createElement('a');
    skipNav.href = '#main';
    skipNav.className = 'skip-nav sr-only focus:not-sr-only';
    skipNav.textContent = 'Skip to main content';
    skipNav.setAttribute('aria-label', 'Skip to main content');
    document.body.insertBefore(skipNav, document.body.firstChild);
}

// Initialize keyboard shortcuts
function initializeKeyboardShortcuts() {
    const shortcuts = {
        'ctrl+k': focusQuickSearch,
        'ctrl+enter': sendFocusedMessage,
        'ctrl+/': showKeyboardHelp,
        'alt+1': () => focusAgent('planner_01'),
        'alt+2': () => focusAgent('coder_01'),
        'alt+3': () => focusAgent('tester_01'),
        'alt+4': () => focusAgent('security_01'),
        'alt+5': () => focusAgent('devops_01'),
        'alt+6': () => focusAgent('general_01'),
        'alt+c': focusCollaborationHub,
        'alt+t': toggleTheme,
        'escape': clearFocus
    };
    
    document.addEventListener('keydown', function(e) {
        const key = getKeyCombo(e);
        
        if (shortcuts[key]) {
            e.preventDefault();
            shortcuts[key]();
        }
    });
    
    // Add keyboard help button
    const helpBtn = document.createElement('button');
    helpBtn.className = 'keyboard-help-btn';
    helpBtn.innerHTML = '<i data-lucide="keyboard" class="w-4 h-4"></i>';
    helpBtn.setAttribute('aria-label', 'Keyboard shortcuts help');
    helpBtn.setAttribute('data-tooltip', 'Keyboard shortcuts (Ctrl+/)');
    helpBtn.onclick = showKeyboardHelp;
    
    const header = document.querySelector('header .flex.items-center.justify-between');
    if (header) {
        header.appendChild(helpBtn);
    }
}

// Get key combination string
function getKeyCombo(e) {
    const keys = [];
    if (e.ctrlKey || e.metaKey) keys.push('ctrl');
    if (e.altKey) keys.push('alt');
    if (e.shiftKey) keys.push('shift');
    
    let key = e.key.toLowerCase();
    if (key === ' ') key = 'space';
    keys.push(key);
    
    return keys.join('+');
}

// Focus quick search (create if doesn't exist)
function focusQuickSearch() {
    let searchInput = document.getElementById('quick-search');
    if (!searchInput) {
        createQuickSearch();
        searchInput = document.getElementById('quick-search');
    }
    searchInput.focus();
}

// Create quick search overlay
function createQuickSearch() {
    const overlay = document.createElement('div');
    overlay.className = 'quick-search-overlay';
    overlay.innerHTML = `
        <div class="quick-search-modal">
            <input type="text" 
                   id="quick-search" 
                   placeholder="Search agents, tasks, or commands..." 
                   class="quick-search-input"
                   aria-label="Quick search">
            <div class="quick-search-results" id="quick-search-results"></div>
            <div class="quick-search-footer">
                <span class="keyboard-shortcut">ESC</span> to close
                <span class="keyboard-shortcut">↑↓</span> to navigate
                <span class="keyboard-shortcut">Enter</span> to select
            </div>
        </div>
    `;
    
    overlay.addEventListener('click', function(e) {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
    
    document.body.appendChild(overlay);
    
    const searchInput = document.getElementById('quick-search');
    searchInput.addEventListener('input', performQuickSearch);
    searchInput.addEventListener('keydown', handleQuickSearchNav);
}

// Send message from focused input
function sendFocusedMessage() {
    const focusedElement = document.activeElement;
    if (focusedElement && focusedElement.classList.contains('chat-input')) {
        const agentId = focusedElement.id.replace('input-', '');
        sendMessageButton(agentId);
    }
}

// Show keyboard shortcuts help
function showKeyboardHelp() {
    const helpModal = document.createElement('div');
    helpModal.className = 'keyboard-help-modal';
    helpModal.innerHTML = `
        <div class="keyboard-help-content">
            <h3>Keyboard Shortcuts</h3>
            <button class="close-btn" onclick="this.parentElement.parentElement.remove()">×</button>
            <div class="shortcuts-grid">
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Ctrl + K</span>
                    <span>Quick search</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Ctrl + Enter</span>
                    <span>Send message</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Alt + 1-6</span>
                    <span>Focus agent 1-6</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Alt + C</span>
                    <span>Focus collaboration hub</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Alt + T</span>
                    <span>Toggle theme</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Tab</span>
                    <span>Navigate forward</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Shift + Tab</span>
                    <span>Navigate backward</span>
                </div>
                <div class="shortcut-item">
                    <span class="keyboard-shortcut">Escape</span>
                    <span>Clear focus / Close modals</span>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(helpModal);
}

// Focus specific agent
function focusAgent(agentId) {
    const agentInput = document.getElementById(`input-${agentId}`);
    if (agentInput) {
        agentInput.focus();
        agentInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Focus collaboration hub
function focusCollaborationHub() {
    const collabTask = document.getElementById('collab-task');
    if (collabTask) {
        collabTask.focus();
        collabTask.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// Clear focus
function clearFocus() {
    document.activeElement.blur();
    // Close any open modals
    document.querySelectorAll('.quick-search-overlay, .keyboard-help-modal').forEach(el => el.remove());
}

// Enhance accessibility with ARIA labels and roles
function enhanceAccessibility() {
    // Add ARIA labels to all buttons without text
    document.querySelectorAll('button').forEach(btn => {
        if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
            const icon = btn.querySelector('i[data-lucide]');
            if (icon) {
                const iconName = icon.getAttribute('data-lucide');
                btn.setAttribute('aria-label', iconName.replace('-', ' '));
            }
        }
    });
    
    // Add ARIA live regions for dynamic content
    const dynamicAreas = [
        { selector: '#collab-results', politeness: 'polite' },
        { selector: '.chat-area', politeness: 'polite' },
        { selector: '.status-indicator', politeness: 'assertive' }
    ];
    
    dynamicAreas.forEach(area => {
        document.querySelectorAll(area.selector).forEach(el => {
            el.setAttribute('aria-live', area.politeness);
            el.setAttribute('aria-atomic', 'true');
        });
    });
    
    // Add proper roles
    document.querySelector('main')?.setAttribute('role', 'main');
    document.querySelector('header')?.setAttribute('role', 'banner');
    
    // Label form elements
    document.querySelectorAll('input, select, textarea').forEach(input => {
        if (!input.getAttribute('aria-label') && !input.labels?.length) {
            const placeholder = input.getAttribute('placeholder');
            if (placeholder) {
                input.setAttribute('aria-label', placeholder);
            }
        }
    });
    
    // Mark decorative icons
    document.querySelectorAll('i[data-lucide]').forEach(icon => {
        if (!icon.closest('button') && !icon.closest('a')) {
            icon.setAttribute('aria-hidden', 'true');
        }
    });
}

// Initialize theme toggle
function initializeThemeToggle() {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Create theme toggle button
    const themeToggle = document.createElement('button');
    themeToggle.className = 'theme-toggle-btn';
    themeToggle.innerHTML = savedTheme === 'dark' 
        ? '<i data-lucide="sun" class="w-4 h-4"></i>' 
        : '<i data-lucide="moon" class="w-4 h-4"></i>';
    themeToggle.setAttribute('aria-label', 'Toggle theme');
    themeToggle.setAttribute('data-tooltip', 'Toggle theme (Alt+T)');
    themeToggle.onclick = toggleTheme;
    
    const header = document.querySelector('header .flex.items-center.space-x-2');
    if (header) {
        header.appendChild(themeToggle);
    }
}

// Toggle theme
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update toggle button icon
    const themeToggle = document.querySelector('.theme-toggle-btn');
    if (themeToggle) {
        themeToggle.innerHTML = newTheme === 'dark' 
            ? '<i data-lucide="sun" class="w-4 h-4"></i>' 
            : '<i data-lucide="moon" class="w-4 h-4"></i>';
        
        // Re-initialize Lucide icons
        if (window.lucide) {
            lucide.createIcons();
        }
    }
    
    // Announce theme change to screen readers
    announceToScreenReader(`Theme changed to ${newTheme} mode`);
}

// Initialize loading states
function initializeLoadingStates() {
    // Loading states are now handled by the API client
    // The API client automatically manages loading indicators and error states
    
    // Add global loading indicator support
    const loadingIndicators = document.querySelectorAll('.loading-indicator');
    loadingIndicators.forEach(indicator => {
        indicator.style.display = 'none';
    });
    
    // Listen for API events if we want to add custom loading behavior
    document.addEventListener('api-request-start', (event) => {
        const { url } = event.detail;
        if (url.includes('/api/agents/chat/')) {
            const agentId = url.split('/').pop();
            const agentWindow = document.getElementById(agentId);
            agentWindow?.classList.add('loading');
        }
    });
    
    document.addEventListener('api-request-end', () => {
        document.querySelectorAll('.loading').forEach(el => {
            el.classList.remove('loading');
        });
    });
}

// Enhance focus management
function enhanceFocusManagement() {
    // Trap focus in modals
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            const modal = document.querySelector('.quick-search-overlay, .keyboard-help-modal');
            if (modal) {
                trapFocus(e, modal);
            }
        }
    });
    
    // Improve focus ring visibility
    document.addEventListener('mousedown', () => {
        document.body.classList.add('mouse-nav');
    });
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            document.body.classList.remove('mouse-nav');
        }
    });
}

// Trap focus within element
function trapFocus(e, container) {
    const focusableElements = container.querySelectorAll(
        'a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];
    
    if (e.shiftKey && document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
    } else if (!e.shiftKey && document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
    }
}

// Add quick action buttons
function addQuickActions() {
    const quickActions = document.createElement('div');
    quickActions.className = 'quick-actions';
    quickActions.innerHTML = `
        <button class="quick-action-btn" 
                aria-label="New collaboration" 
                data-tooltip="New collaboration"
                onclick="focusCollaborationHub()">
            <i data-lucide="plus" class="w-6 h-6"></i>
        </button>
        <button class="quick-action-btn secondary" 
                aria-label="Quick search" 
                data-tooltip="Quick search (Ctrl+K)"
                onclick="focusQuickSearch()">
            <i data-lucide="search" class="w-6 h-6"></i>
        </button>
    `;
    
    document.body.appendChild(quickActions);
    
    // Re-initialize Lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }
}

// Initialize tooltips
function initializeTooltips() {
    // Simple CSS-based tooltips are already handled by data-tooltip attribute
    // This function can be extended for more complex tooltip functionality
}

// Announce to screen readers
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    setTimeout(() => {
        announcement.remove();
    }, 1000);
}

// Add necessary styles
const styleSheet = document.createElement('style');
styleSheet.textContent = `
/* Quick Search Overlay */
.quick-search-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 10vh;
    z-index: 1000;
}

.quick-search-modal {
    background: var(--bg-primary);
    border-radius: 12px;
    box-shadow: var(--shadow-xl);
    width: 90%;
    max-width: 600px;
    max-height: 70vh;
    display: flex;
    flex-direction: column;
}

.quick-search-input {
    padding: var(--space-lg);
    border: none;
    border-bottom: 1px solid var(--border-color);
    font-size: 1.125rem;
    background: transparent;
    color: var(--text-primary);
}

.quick-search-results {
    flex: 1;
    overflow-y: auto;
    padding: var(--space-md);
}

.quick-search-footer {
    padding: var(--space-md);
    border-top: 1px solid var(--border-color);
    display: flex;
    gap: var(--space-md);
    font-size: 0.875rem;
    color: var(--text-secondary);
}

/* Keyboard Help Modal */
.keyboard-help-modal {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.keyboard-help-content {
    background: var(--bg-primary);
    border-radius: 12px;
    padding: var(--space-xl);
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
    position: relative;
}

.keyboard-help-content h3 {
    margin: 0 0 var(--space-lg);
    color: var(--text-primary);
}

.close-btn {
    position: absolute;
    top: var(--space-md);
    right: var(--space-md);
    background: none;
    border: none;
    font-size: 1.5rem;
    color: var(--text-secondary);
    cursor: pointer;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
}

.close-btn:hover {
    background: var(--bg-secondary);
}

.shortcuts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: var(--space-md);
}

.shortcut-item {
    display: flex;
    align-items: center;
    gap: var(--space-md);
    color: var(--text-secondary);
}

/* Theme Toggle Button */
.theme-toggle-btn,
.keyboard-help-btn {
    background: none;
    border: none;
    padding: var(--space-sm);
    border-radius: 8px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.theme-toggle-btn:hover,
.keyboard-help-btn:hover {
    background: var(--bg-secondary);
    color: var(--text-primary);
}

/* Mouse navigation - hide focus rings */
body.mouse-nav *:focus {
    outline: none;
}

body.mouse-nav *:focus-visible {
    outline: 2px solid var(--border-focus);
}

/* Loading enhancements */
.agent-window.loading {
    position: relative;
}

.agent-window.loading::after {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(255, 255, 255, 0.8);
    border-radius: inherit;
    display: flex;
    align-items: center;
    justify-content: center;
}

[data-theme="dark"] .agent-window.loading::after {
    background: rgba(0, 0, 0, 0.8);
}
`;

document.head.appendChild(styleSheet);
//# sourceMappingURL=ux-enhancements.js.map
