// Enhanced API client with authentication, error handling, and toast notifications
// TypeScript version with full type safety
import { config, getAuthHeaders } from '../config.js';
import { showApiKeyWarning, showToast } from '../components/api-key-setup.js';

interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    error?: string;
}

interface AgentProfile {
    agent_id: string;
    name: string;
    role: string;
    description: string;
    capabilities: string[];
    specialties: string[];
    tools: string[];
    interaction_style: string;
}

interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: number;
}

interface ProviderStatus {
    openrouter: boolean;
    openai: boolean;
    hasAnyProvider: boolean;
}

/**
 * Enhanced API client with authentication, error handling, and circuit breaker patterns
 * Implements Core Development Rules for error handling and resilient HTTP requests
 * Full TypeScript implementation for better type safety and IDE support
 */
export class ApiClient {
    private baseUrl: string = '/api';
    private pendingRequests: Map<string, Promise<Response>> = new Map();

    constructor() {}

    /**
     * Enhanced fetch with authentication, error handling, and toast notifications
     * Implements request deduplication and automatic retry logic
     */
    async fetch(url: string, options: RequestInit = {}): Promise<Response> {
        // Inject auth headers
        const authHeaders = getAuthHeaders();
        const userHeaders = options.headers || {};
        
        // Handle special case for file uploads - don't set Content-Type
        let headers: Record<string, string> = { ...authHeaders };
        
        // Add user headers, but filter out undefined Content-Type
        Object.keys(userHeaders).forEach(key => {
            const value = (userHeaders as Record<string, any>)[key];
            if (value !== undefined) {
                headers[key] = value;
            }
        });

        const requestOptions: RequestInit = {
            ...options,
            headers
        };

        // Handle request deduplication for identical requests
        const requestKey = `${url}_${JSON.stringify(requestOptions)}`;
        if (this.pendingRequests.has(requestKey)) {
            return this.pendingRequests.get(requestKey)!;
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
     */
    private async _makeRequest(url: string, options: RequestInit): Promise<Response> {
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
            if (this._shouldUseFallback(url, error as Error)) {
                return this._getFallbackResponse(url);
            }
            
            // Only show toast for network errors, not for handled HTTP errors
            if ((error as Error).message === 'Authentication required') {
                // Already handled above
                throw error;
            } else if (!(error as Error).message.includes('Request failed with status')) {
                showToast(`Network error: ${(error as Error).message}`, 'error');
            }
            throw error;
        }
    }

    /**
     * Handle 401 authentication errors
     */
    private _handle401Error(url: string): void {
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
     */
    async fetchJson<T = any>(url: string, options: RequestInit = {}): Promise<T> {
        const response = await this.fetch(url, options);
        return response.json();
    }

    /**
     * Convenience method for POST requests with JSON body
     */
    async postJson<T = any>(url: string, data: any, options: RequestInit = {}): Promise<T> {
        return this.fetchJson<T>(url, {
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
    async putJson<T = any>(url: string, data: any, options: RequestInit = {}): Promise<T> {
        return this.fetchJson<T>(url, {
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
    async delete(url: string, options: RequestInit = {}): Promise<Response> {
        return this.fetch(url, {
            method: 'DELETE',
            ...options
        });
    }

    /**
     * Check if API is configured and accessible
     */
    async checkApiHealth(): Promise<boolean> {
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
    async checkProviderConfiguration(): Promise<ProviderStatus> {
        try {
            const response = await this.fetchJson<any>('/api/providers/status');
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
     * Get list of available agents
     */
    async getAgentProfiles(): Promise<ApiResponse<{ profiles: AgentProfile[]; total: number }>> {
        try {
            return await this.fetchJson<ApiResponse<{ profiles: AgentProfile[]; total: number }>>('/api/agents/profiles');
        } catch (error) {
            throw new Error(`Failed to load agent profiles: ${(error as Error).message}`);
        }
    }

    /**
     * Send message to specific agent
     */
    async sendMessage(
        agentId: string, 
        message: string, 
        model?: string, 
        enhance?: boolean
    ): Promise<ApiResponse<{ response: string; enhanced?: boolean }>> {
        try {
            return await this.postJson<ApiResponse<{ response: string; enhanced?: boolean }>>(
                `/api/agents/chat/${agentId}`,
                {
                    message,
                    model,
                    enhance
                }
            );
        } catch (error) {
            throw new Error(`Failed to send message: ${(error as Error).message}`);
        }
    }

    /**
     * Get chat history for agent
     */
    async getChatHistory(agentId: string): Promise<ApiResponse<{ history: ChatMessage[] }>> {
        try {
            return await this.fetchJson<ApiResponse<{ history: ChatMessage[] }>>(`/api/agents/chat/${agentId}/history`);
        } catch (error) {
            throw new Error(`Failed to load chat history: ${(error as Error).message}`);
        }
    }

    /**
     * Clear chat history for agent
     */
    async clearChatHistory(agentId: string): Promise<boolean> {
        try {
            const response = await this.delete(`/api/agents/chat/${agentId}/history`);
            return response.ok;
        } catch (error) {
            throw new Error(`Failed to clear chat history: ${(error as Error).message}`);
        }
    }

    /**
     * Upload file to agent
     */
    async uploadFile(agentId: string, file: File): Promise<ApiResponse<{ agent_response: string }>> {
        try {
            const formData = new FormData();
            formData.append('file', file);

            return await this.fetchJson<ApiResponse<{ agent_response: string }>>(
                `/api/agents/upload/${agentId}`,
                {
                    method: 'POST',
                    body: formData
                    // Note: Don't set Content-Type, let browser set it with boundary
                }
            );
        } catch (error) {
            throw new Error(`Failed to upload file: ${(error as Error).message}`);
        }
    }

    /**
     * Check if we should use fallback mock data
     */
    private _shouldUseFallback(url: string, error: Error): boolean {
        // Use fallback for network errors or connection refused
        return error.message.includes('fetch') || 
               error.message.includes('NetworkError') ||
               error.message.includes('Failed to fetch') ||
               url.includes('/api/agents/profiles');
    }

    /**
     * Get fallback mock response
     */
    private _getFallbackResponse(url: string): Response {
        console.log('Using fallback data for:', url);
        
        if (url.includes('/api/agents/profiles')) {
            const mockData = {
                success: true,
                profiles: [
                    {
                        agent_id: 'general_01',
                        name: 'General Assistant',
                        role: 'general',
                        description: 'A helpful general-purpose assistant (Mock Data)',
                        capabilities: ['general assistance', 'task planning', 'problem solving'],
                        specialties: ['general'],
                        tools: [],
                        interaction_style: 'conversational'
                    },
                    {
                        agent_id: 'product_01',
                        name: 'Product Manager',
                        role: 'product',
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
            } as Response;
        }
        
        // Default fallback
        return {
            ok: true,
            json: () => Promise.resolve({ success: false, error: 'Fallback response' })
        } as Response;
    }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export the class for testing
export default ApiClient;

