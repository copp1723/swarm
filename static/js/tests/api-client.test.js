// API Client Tests
import { ApiClient } from '../services/api-client.js';
import { config } from '../config.js';

describe('ApiClient', () => {
    let apiClient;
    let mockFetch;

    beforeEach(() => {
        apiClient = new ApiClient();
        mockFetch = jest.fn();
        global.fetch = mockFetch;
        
        // Mock DOM methods
        global.document = {
            body: { insertAdjacentHTML: jest.fn() },
            getElementById: jest.fn(() => ({ remove: jest.fn() })),
            createElement: jest.fn(() => ({ 
                id: '', 
                classList: { remove: jest.fn(), add: jest.fn() },
                remove: jest.fn()
            }))
        };
        
        // Mock localStorage
        global.localStorage = {
            getItem: jest.fn(),
            setItem: jest.fn(),
            removeItem: jest.fn()
        };
        
        // Mock config
        config.API_KEY = 'test-api-key';
        config.AUTH_ENABLED = true;
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('fetch method', () => {
        it('should inject auth headers', async () => {
            const mockResponse = { ok: true, json: () => Promise.resolve({ success: true }) };
            mockFetch.mockResolvedValue(mockResponse);

            await apiClient.fetch('/api/test');

            expect(mockFetch).toHaveBeenCalledWith('/api/test', {
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-api-key'
                }
            });
        });

        it('should handle 401 errors', async () => {
            const mockResponse = { ok: false, status: 401 };
            mockFetch.mockResolvedValue(mockResponse);

            await expect(apiClient.fetch('/api/test')).rejects.toThrow('Authentication required');
        });

        it('should handle network errors', async () => {
            mockFetch.mockRejectedValue(new Error('Network error'));

            await expect(apiClient.fetch('/api/test')).rejects.toThrow('Network error');
        });

        it('should handle API key errors for chat endpoint', async () => {
            const mockResponse = { 
                ok: false, 
                status: 403,
                clone: () => ({
                    json: () => Promise.resolve({ error: 'API key required' })
                })
            };
            mockFetch.mockResolvedValue(mockResponse);

            await expect(apiClient.fetch('/api/agents/chat/test')).rejects.toThrow();
        });
    });

    describe('convenience methods', () => {
        beforeEach(() => {
            const mockResponse = { 
                ok: true, 
                json: () => Promise.resolve({ success: true }) 
            };
            mockFetch.mockResolvedValue(mockResponse);
        });

        it('should handle JSON POST requests', async () => {
            const data = { message: 'test' };
            await apiClient.postJson('/api/test', data);

            expect(mockFetch).toHaveBeenCalledWith('/api/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-api-key'
                },
                body: JSON.stringify(data)
            });
        });

        it('should handle PUT requests', async () => {
            const data = { message: 'test' };
            await apiClient.putJson('/api/test', data);

            expect(mockFetch).toHaveBeenCalledWith('/api/test', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-api-key'
                },
                body: JSON.stringify(data)
            });
        });

        it('should handle DELETE requests', async () => {
            await apiClient.delete('/api/test');

            expect(mockFetch).toHaveBeenCalledWith('/api/test', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-api-key'
                }
            });
        });
    });

    describe('health checks', () => {
        it('should check API health', async () => {
            const mockResponse = { ok: true };
            mockFetch.mockResolvedValue(mockResponse);

            const isHealthy = await apiClient.checkApiHealth();
            
            expect(isHealthy).toBe(true);
            expect(mockFetch).toHaveBeenCalledWith('/api/health', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-api-key',
                    'X-Skip-Error-Toast': 'true'
                }
            });
        });

        it('should handle health check failures', async () => {
            mockFetch.mockRejectedValue(new Error('Network error'));

            const isHealthy = await apiClient.checkApiHealth();
            
            expect(isHealthy).toBe(false);
        });
    });

    describe('provider configuration', () => {
        it('should check provider configuration', async () => {
            const mockResponse = { 
                ok: true,
                json: () => Promise.resolve({
                    openrouter_configured: true,
                    openai_configured: false
                })
            };
            mockFetch.mockResolvedValue(mockResponse);

            const config = await apiClient.checkProviderConfiguration();
            
            expect(config).toEqual({
                openrouter: true,
                openai: false,
                hasAnyProvider: true
            });
        });

        it('should handle provider configuration failures', async () => {
            mockFetch.mockRejectedValue(new Error('Network error'));

            const config = await apiClient.checkProviderConfiguration();
            
            expect(config).toEqual({
                openrouter: false,
                openai: false,
                hasAnyProvider: false
            });
        });
    });

    describe('request deduplication', () => {
        it('should deduplicate identical requests', async () => {
            const mockResponse = { ok: true, json: () => Promise.resolve({ success: true }) };
            mockFetch.mockResolvedValue(mockResponse);

            const url = '/api/test';
            const options = { method: 'GET' };

            // Make two identical requests simultaneously
            const [result1, result2] = await Promise.all([
                apiClient.fetch(url, options),
                apiClient.fetch(url, options)
            ]);

            // Should only have made one actual fetch call
            expect(mockFetch).toHaveBeenCalledTimes(1);
            expect(result1).toBe(result2); // Should return the same response
        });
    });
});

