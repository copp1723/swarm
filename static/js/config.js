// Configuration for the frontend
export const config = {
    // API Key - Replace with your actual API key from the server logs
    // When you start the server, look for "Development API Key: swarm_dev_default_..."
    API_KEY: localStorage.getItem('swarm_api_key') || '',
    
    // Base URLs
    API_BASE_URL: '/api',
    WS_URL: `ws://${window.location.host}`,
    
    // Feature flags
    AUTH_ENABLED: true,
    DEBUG_MODE: true
};

// Helper to set API key
export function setApiKey(key) {
    localStorage.setItem('swarm_api_key', key);
    config.API_KEY = key;
    console.log('API key updated');
}

// Helper to get auth headers
export function getAuthHeaders() {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (config.AUTH_ENABLED && config.API_KEY) {
        headers['X-API-Key'] = config.API_KEY;
    }
    
    return headers;
}
//# sourceMappingURL=config.js.map
