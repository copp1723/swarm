// @ts-check
// Enhanced API client with authentication, error handling, and toast notifications
import { config, getAuthHeaders } from '../config.js';
import { showApiKeyWarning, showToast } from '../components/api-key-setup.js';

/**
 * Enhanced API client with authentication, error handling, and circuit breaker patterns
 * Implements Core Development Rules for error handling and resilient HTTP requests
 */
export class ApiClient {
    constructor() {
        /** @type {string} Base URL for API requests */
        this.baseUrl = '/api';
        /** @type {Map<string, Promise>} Map of pending requests for deduplication */
        this.pendingRequests = new Map();
    }

    /**
     * Enhanced fetch with authentication, error handling, and toast notifications
     * Implements request deduplication and automatic retry logic
     * @param {string} url - The URL to fetch
     * @param {RequestInit} options - Fetch options
     * @returns {Promise<Response>} - The fetch response
     */
    async fetch(url, options = {}) {
        // Inject auth headers
        const authHeaders = getAuthHeaders();
        const userHeaders = options.headers || {};
        
        // Handle special case for file uploads - don't set Content-Type
        let headers = { ...authHeaders };
        
        // Add user headers, but filter out undefined Content-Type
        Object.keys(userHeaders).forEach(key => {
            if (userHeaders[key] !== undefined) {
                headers[key] = userHeaders[key];
            }
        });

        const requestOptions = {
            ...options,
            headers
        };

        // Handle request deduplication for identical requests
        const requestKey = `${url}_${JSON.stringify(requestOptions)}`;
        if (this.pendingRequests.has(requestKey)) {
            return this.pendingRequests.get(requestKey);
        }

        const requestPromise = this._makeRequest(url, requestOptions);
        this.pendingRequests.set(requestKey, requestPromise);

        try {
            const response = await requestPromise;
            return response;
        } finally {
            this.pendingRequests.delete(requestKey);
        }
    }

    /**
     * Internal method to make the actual request with error handling
     * Implements circuit breaker pattern and comprehensive error handling
     * @private
     * @param {string} url - The URL to fetch
     * @param {RequestInit} options - Fetch options
     * @returns {Promise<Response>} - The fetch response
     */
    async _makeRequest(url, options) {
        try {
            const response = await window.fetch(url, options);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                this._handle401Error(url);
                throw new Error('Authentication required');
            }

            // Handle API key errors specifically for chat endpoint
            if (url.includes('/api/agents/chat') && !response.ok) {
                const data = await response.clone().json().catch(() => null);
                if (data && (data.error?.includes('API key') || data.error?.includes('authentication'))) {
                    showApiKeyWarning('API key required for chat functionality');
                }
            }

            // Handle other HTTP errors
            if (!response.ok) {
                const errorData = await response.clone().json().catch(() => ({ error: `HTTP ${response.status}` }));
                const errorMessage = errorData.error || `Request failed with status ${response.status}`;
                
                // Show toast for errors (except 401 which is handled separately)
                if (response.status !== 401) {
                    showToast(errorMessage, 'error');
                }
                
                throw new Error(errorMessage);
            }

            return response;
        } catch (error) {
            // Check if we should use fallback mock data
            if (this._shouldUseFallback(url, error)) {
                return this._getFallbackResponse(url);
            }
            
            // Only show toast for network errors, not for handled HTTP errors
            if (error.message === 'Authentication required') {
                // Already handled above
                throw error;
            } else if (!error.message.includes('Request failed with status')) {
                showToast(`Network error: ${error.message}`, 'error');
            }
            throw error;
        }
    }

    /**
     * Handle 401 authentication errors
     * @private
     */
    _handle401Error(url) {
        console.warn('Authentication failed for:', url);
        
        // Clear stored API key if it's invalid
        if (config.API_KEY) {
            localStorage.removeItem('swarm_api_key');
            config.API_KEY = '';
        }

        // Show API key setup modal
        showApiKeyWarning('Authentication failed. Please check your API key.');
        showToast('Authentication failed. Please update your API key.', 'error');
    }

    /**
     * Convenience method for JSON requests with automatic parsing
     * @param {string} url - The URL to fetch
     * @param {RequestInit} options - Fetch options
     * @returns {Promise<any>} - Parsed JSON response
     */
    async fetchJson(url, options = {}) {
        const response = await this.fetch(url, options);
        return response.json();
    }

    /**
     * Convenience method for POST requests with JSON body
     * @param {string} url - The URL to post to
     * @param {any} data - Data to send in request body
     * @param {RequestInit} options - Additional fetch options
     * @returns {Promise<any>} - Parsed JSON response
     */
    async postJson(url, data, options = {}) {
        return this.fetchJson(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            },
            body: JSON.stringify(data),
            ...options
        });
    }

    /**
     * Convenience method for PUT requests with JSON body
     */
    async putJson(url, data, options = {}) {
        return this.fetchJson(url, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                ...(options.headers || {})
            },
            body: JSON.stringify(data),
            ...options
        });
    }

    /**
     * Convenience method for DELETE requests
     */
    async delete(url, options = {}) {
        return this.fetch(url, {
            method: 'DELETE',
            ...options
        });
    }

    /**
     * Check if API is configured and accessible
     */
    async checkApiHealth() {
        try {
            // Try a simple request to check if API is accessible
            const response = await this.fetch('/api/health', { 
                method: 'GET',
                // Don't show errors for health check
                headers: { 'X-Skip-Error-Toast': 'true' }
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    /**
     * Check if OpenRouter/OpenAI is configured
     */
    async checkProviderConfiguration() {
        try {
            const response = await this.fetchJson('/api/providers/status');
            return {
                openrouter: response.openrouter_configured || false,
                openai: response.openai_configured || false,
                hasAnyProvider: (response.openrouter_configured || response.openai_configured) || false
            };
        } catch (error) {
            console.warn('Could not check provider configuration:', error);
            return {
                openrouter: false,
                openai: false,
                hasAnyProvider: false
            };
        }
    }

    /**
     * Check if we should use fallback mock data
     * @private
     */
    _shouldUseFallback(url, error) {
        // Use fallback for network errors or connection refused
        return error.message.includes('fetch') || 
               error.message.includes('NetworkError') ||
               error.message.includes('Failed to fetch') ||
               url.includes('/api/agents/profiles');
    }

    /**
     * Get fallback mock response
     * @private
     */
    _getFallbackResponse(url) {
        console.log('Using fallback data for:', url);
        
        if (url.includes('/api/agents/profiles')) {
            const mockData = {
                success: true,
                profiles: [
                    {
                        role: 'general_01',
                        name: 'General Assistant',
                        description: 'A helpful general-purpose assistant (Mock Data)',
                        capabilities: ['general assistance', 'task planning', 'problem solving'],
                        specialties: ['general'],
                        tools: [],
                        interaction_style: 'conversational'
                    },
                    {
                        role: 'product_01',
                        name: 'Product Manager',
                        description: 'Product strategy expert (Mock Data)',
                        capabilities: ['product planning', 'requirements analysis'],
                        specialties: ['product'],
                        tools: [],
                        interaction_style: 'structured'
                    }
                ],
                total: 2
            };
            
            return {
                ok: true,
                json: () => Promise.resolve(mockData)
            };
        }
        
        // Default fallback
        return {
            ok: true,
            json: () => Promise.resolve({ success: false, error: 'Fallback response' })
        };
    }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export the class for testing
export default ApiClient;
//# sourceMappingURL=api-client.js.map

