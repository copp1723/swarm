// Main initialization script for API client and provider status
import { apiClient } from './services/api-client.js';
import { initApiKeySetup, showProviderWarning, updateUIForProviderStatus, showToast } from './components/api-key-setup.js';

// Initialize the application
async function initApp() {
    // Initialize API key setup if needed
    initApiKeySetup();
    
    // Check provider configuration
    await checkProviderConfiguration();
    
    // Set up periodic health checks
    setupHealthChecks();
    
    console.log('Application initialized successfully');
}

/**
 * Check and handle provider configuration status
 */
async function checkProviderConfiguration() {
    try {
        const providerStatus = await apiClient.checkProviderConfiguration();
        
        // Show warning if no providers are configured
        showProviderWarning(providerStatus);
        
        // Update UI based on provider status
        updateUIForProviderStatus(providerStatus);
        
        // Store status globally for other components to use
        window.providerStatus = providerStatus;
        
        console.log('Provider status:', providerStatus);
    } catch (error) {
        console.warn('Could not check provider configuration:', error);
        
        // Assume degraded state if we can't check
        const degradedStatus = {
            openrouter: false,
            openai: false,
            hasAnyProvider: false
        };
        
        showProviderWarning(degradedStatus);
        updateUIForProviderStatus(degradedStatus);
        window.providerStatus = degradedStatus;
    }
}

/**
 * Set up periodic health checks for API and providers
 */
function setupHealthChecks() {
    // Check API health every 30 seconds
    setInterval(async () => {
        const isHealthy = await apiClient.checkApiHealth();
        
        // Update global API health status
        window.apiHealthy = isHealthy;
        
        // If API is healthy, also check provider status every 5 minutes
        if (isHealthy) {
            const now = Date.now();
            const lastProviderCheck = window.lastProviderCheck || 0;
            
            if (now - lastProviderCheck > 300000) { // 5 minutes
                await checkProviderConfiguration();
                window.lastProviderCheck = now;
            }
        }
    }, 30000);
}

/**
 * Handle degraded functionality when providers are not configured
 */
function setupDegradedMode() {
    // Add CSS class to body to indicate degraded mode
    document.body.classList.add('provider-degraded');
    
    // Override functions that depend on providers
    const originalSendMessage = window.sendMessage;
    if (originalSendMessage) {
        window.sendMessage = function(event, agentId) {
            if (!window.providerStatus?.hasAnyProvider) {
                showToast('AI providers not configured. Please configure OpenRouter or OpenAI.', 'warning');
                return;
            }
            return originalSendMessage.call(this, event, agentId);
        };
    }
}

/**
 * Add global CSS for degraded states
 */
function addDegradedStyles() {
    const styles = `
        /* Provider degraded styles */
        .provider-degraded .send-button:disabled,
        .provider-degraded .model-selector option:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .provider-degraded .chat-interface::before {
            content: "⚠️ AI provider not configured";
            position: absolute;
            top: 10px;
            right: 10px;
            background: #fef3c7;
            color: #92400e;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10;
        }
        
        .provider-degraded .agent-window {
            border-color: #fbbf24;
        }
        
        .provider-degraded .collaboration-hub {
            opacity: 0.7;
        }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Add degraded styles
addDegradedStyles();

// Export for use by other modules
export { initApp, checkProviderConfiguration };
//# sourceMappingURL=init.js.map

