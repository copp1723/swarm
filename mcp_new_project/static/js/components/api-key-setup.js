// API Key Setup Component
import { config, setApiKey } from '../config.js';

export function initApiKeySetup() {
    // Check if API key is already set
    if (config.API_KEY) {
        console.log('API key already configured');
        return;
    }
    
    // Create setup UI
    const setupHtml = `
        <div id="api-key-setup" class="fixed top-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded-lg shadow-lg z-50" style="max-width: 400px;">
            <div class="flex items-start">
                <svg class="w-6 h-6 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
                </svg>
                <div class="flex-1">
                    <p class="font-bold">API Key Required</p>
                    <p class="text-sm mt-1">Please enter your API key from the server logs:</p>
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
                    </div>
                    <p class="text-xs mt-2">Look for "Development API Key:" in your terminal</p>
                </div>
            </div>
        </div>
    `;
    
    // Add to page
    document.body.insertAdjacentHTML('beforeend', setupHtml);
    
    // Add event listeners
    document.getElementById('save-api-key').addEventListener('click', () => {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (apiKey) {
            setApiKey(apiKey);
            document.getElementById('api-key-setup').remove();
            showSuccessMessage('API key saved successfully!');
        } else {
            alert('Please enter an API key');
        }
    });
    
    document.getElementById('skip-api-key').addEventListener('click', () => {
        config.AUTH_ENABLED = false;
        document.getElementById('api-key-setup').remove();
        console.log('Authentication disabled');
    });
    
    // Auto-save if enter is pressed
    document.getElementById('api-key-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('save-api-key').click();
        }
    });
}

function showSuccessMessage(message) {
    const successHtml = `
        <div id="success-message" class="fixed top-4 right-4 bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg shadow-lg z-50">
            ${message}
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', successHtml);
    setTimeout(() => {
        document.getElementById('success-message')?.remove();
    }, 3000);
}