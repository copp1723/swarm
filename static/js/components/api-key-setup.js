// API Key Setup Component
import { config, setApiKey } from '../config.js';

let warningBannerVisible = false;
let currentProviderStatus = null;

export function initApiKeySetup() {
    // Check if API key is already set
    if (config.API_KEY) {
        console.log('API key already configured');
        return;
    }
    
    showApiKeySetup();
}

/**
 * Show the API key setup modal
 */
export function showApiKeySetup(message = 'Please enter your API key from the server logs:') {
    // Remove existing setup if present
    document.getElementById('api-key-setup')?.remove();
    
    // Create setup UI
    const setupHtml = `
        <div id="api-key-setup" class="fixed top-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded-lg shadow-lg z-50" style="max-width: 400px;">
            <div class="flex items-start">
                <svg class="w-6 h-6 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                </svg>
                <div class="flex-1">
                    <p class="font-bold">API Key Required</p>
                    <p class="text-sm mt-1">${message}</p>
                    <input type="text" 
                           id="api-key-input" 
                           class="mt-2 w-full px-3 py-2 border border-yellow-400 rounded-md text-sm"
                           placeholder="swarm_dev_default_..." 
                           value="${localStorage.getItem('swarm_api_key') || ''}">
                    <div class="mt-2 flex gap-2">
                        <button id="save-api-key" class="px-3 py-1 bg-yellow-600 text-white rounded-md text-sm hover:bg-yellow-700">
                            Save
                        </button>
                        <button id="skip-api-key" class="px-3 py-1 bg-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-400">
                            Skip (No Auth)
                        </button>
                        <button id="close-api-key" class="px-3 py-1 bg-gray-300 text-gray-700 rounded-md text-sm hover:bg-gray-400">
                            ×
                        </button>
                    </div>
                    <p class="text-xs mt-2">Look for "Development API Key:" in your terminal</p>
                </div>
            </div>
        </div>
    `;
    
    // Add to page
    document.body.insertAdjacentHTML('beforeend', setupHtml);
    
    // Add event listeners
    document.getElementById('save-api-key').addEventListener('click', handleSaveApiKey);
    document.getElementById('skip-api-key').addEventListener('click', handleSkipApiKey);
    document.getElementById('close-api-key').addEventListener('click', handleCloseApiKey);
    
    // Auto-save if enter is pressed
    document.getElementById('api-key-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSaveApiKey();
        }
    });
    
    // Focus the input
    setTimeout(() => {
        document.getElementById('api-key-input')?.focus();
    }, 100);
}

/**
 * Show a non-blocking warning banner for API key issues
 */
export function showApiKeyWarning(message) {
    if (warningBannerVisible) {
        return; // Don't show multiple warnings
    }
    
    warningBannerVisible = true;
    
    // Remove existing warning
    document.getElementById('api-key-warning')?.remove();
    
    const warningHtml = `
        <div id="api-key-warning" class="fixed top-4 left-1/2 transform -translate-x-1/2 bg-orange-100 border border-orange-400 text-orange-700 px-4 py-3 rounded-lg shadow-lg z-40" style="max-width: 500px;">
            <div class="flex items-center justify-between">
                <div class="flex items-center">
                    <svg class="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                    </svg>
                    <div>
                        <p class="text-sm font-medium">${message}</p>
                        <button id="open-settings" class="text-xs text-orange-600 hover:text-orange-800 underline mt-1">
                            Open Settings
                        </button>
                    </div>
                </div>
                <button id="dismiss-warning" class="ml-4 text-orange-600 hover:text-orange-800">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', warningHtml);
    
    // Add event listeners
    document.getElementById('open-settings').addEventListener('click', () => {
        showApiKeySetup('Please enter or update your API key:');
        dismissWarning();
    });
    
    document.getElementById('dismiss-warning').addEventListener('click', dismissWarning);
    
    // Auto-dismiss after 10 seconds
    setTimeout(dismissWarning, 10000);
}

/**
 * Show provider configuration warning when OpenRouter/OpenAI is not configured
 */
export function showProviderWarning(providerStatus) {
    currentProviderStatus = providerStatus;
    
    if (providerStatus.hasAnyProvider) {
        document.getElementById('provider-warning')?.remove();
        return;
    }
    
    // Remove existing warning
    document.getElementById('provider-warning')?.remove();
    
    const warningHtml = `
        <div id="provider-warning" class="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-4">
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <div>
                    <p class="text-sm font-medium">AI Provider Not Configured</p>
                    <p class="text-xs mt-1">OpenRouter and OpenAI are not configured. Chat functionality will be limited.</p>
                    <p class="text-xs mt-1">Please configure at least one provider in your environment variables.</p>
                </div>
                <button id="dismiss-provider-warning" class="ml-auto text-yellow-600 hover:text-yellow-800">
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                </button>
            </div>
        </div>
    `;
    
    // Insert at the top of the main content area
    const mainContent = document.querySelector('main') || document.body;
    const firstChild = mainContent.firstElementChild;
    if (firstChild) {
        firstChild.insertAdjacentHTML('beforebegin', warningHtml);
    } else {
        mainContent.insertAdjacentHTML('afterbegin', warningHtml);
    }
    
    document.getElementById('dismiss-provider-warning').addEventListener('click', () => {
        document.getElementById('provider-warning')?.remove();
    });
}

/**
 * Show toast notifications
 */
export function showToast(message, type = 'info', duration = 5000) {
    const toastId = `toast-${Date.now()}`;
    const bgColor = {
        'success': 'bg-green-100 border-green-400 text-green-700',
        'error': 'bg-red-100 border-red-400 text-red-700',
        'warning': 'bg-yellow-100 border-yellow-400 text-yellow-700',
        'info': 'bg-blue-100 border-blue-400 text-blue-700'
    }[type] || 'bg-gray-100 border-gray-400 text-gray-700';
    
    const icon = {
        'success': '✓',
        'error': '✕',
        'warning': '⚠',
        'info': 'ℹ'
    }[type] || 'ℹ';
    
    const toastHtml = `
        <div id="${toastId}" class="fixed bottom-4 right-4 ${bgColor} px-4 py-3 rounded-lg shadow-lg z-50 max-w-sm transform translate-y-2 opacity-0 transition-all duration-300">
            <div class="flex items-center">
                <span class="text-lg mr-2">${icon}</span>
                <span class="text-sm">${message}</span>
                <button class="ml-2 text-lg leading-none" onclick="document.getElementById('${toastId}').remove()">
                    ×
                </button>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', toastHtml);
    
    // Animate in
    const toast = document.getElementById(toastId);
    setTimeout(() => {
        toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);
    
    // Auto-remove
    setTimeout(() => {
        if (toast) {
            toast.classList.add('translate-y-2', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }
    }, duration);
}

/**
 * Update UI based on provider configuration status
 */
export function updateUIForProviderStatus(providerStatus) {
    // Add degraded state classes to chat interfaces
    const chatElements = document.querySelectorAll('.chat-interface, .agent-window, .collaboration-hub');
    
    chatElements.forEach(element => {
        if (providerStatus.hasAnyProvider) {
            element.classList.remove('provider-degraded');
        } else {
            element.classList.add('provider-degraded');
        }
    });
    
    // Disable/enable send buttons
    const sendButtons = document.querySelectorAll('[onclick*="sendMessage"], .send-button');
    sendButtons.forEach(button => {
        if (providerStatus.hasAnyProvider) {
            button.disabled = false;
            button.title = '';
        } else {
            button.disabled = true;
            button.title = 'AI provider not configured';
        }
    });
    
    // Update model selectors
    const modelSelectors = document.querySelectorAll('.model-selector');
    modelSelectors.forEach(selector => {
        const options = selector.querySelectorAll('option');
        options.forEach(option => {
            const value = option.value;
            if (value.includes('openai/') && !providerStatus.openai) {
                option.disabled = true;
                option.textContent += ' (not configured)';
            }
            if (value.includes('openrouter/') && !providerStatus.openrouter) {
                option.disabled = true;
                option.textContent += ' (not configured)';
            }
        });
    });
}

// Event handlers
function handleSaveApiKey() {
    const apiKey = document.getElementById('api-key-input').value.trim();
    if (apiKey) {
        setApiKey(apiKey);
        document.getElementById('api-key-setup').remove();
        showToast('API key saved successfully!', 'success');
    } else {
        showToast('Please enter an API key', 'warning');
    }
}

function handleSkipApiKey() {
    config.AUTH_ENABLED = false;
    document.getElementById('api-key-setup').remove();
    showToast('Authentication disabled', 'info');
    console.log('Authentication disabled');
}

function handleCloseApiKey() {
    document.getElementById('api-key-setup').remove();
}

function dismissWarning() {
    document.getElementById('api-key-warning')?.remove();
    warningBannerVisible = false;
}

// Legacy support
function showSuccessMessage(message) {
    showToast(message, 'success');
}
//# sourceMappingURL=api-key-setup.js.map
