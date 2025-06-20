# API Client Standardization

This document describes the standardized API client implementation that centralizes all API interactions, authentication, error handling, and UI feedback.

## Overview

The API client standardization involves:

1. **Unified API Client** (`/static/js/services/api-client.js`) - Wraps all fetch calls with authentication, error handling, and toast notifications
2. **Enhanced API Key Setup** (`/static/js/components/api-key-setup.js`) - Provides comprehensive API key management and provider warnings
3. **Graceful Degradation** - UI adapts when OpenRouter/OpenAI providers are not configured
4. **Centralized Error Handling** - Consistent error states and user feedback across the application

## Key Features

### 1. Authentication Injection

All API requests automatically include authentication headers:

```javascript
import { apiClient } from './services/api-client.js';

// Automatic auth header injection
const response = await apiClient.fetchJson('/api/agents/status');
```

### 2. Error Handling

- **401 Unauthorized**: Automatically shows API key setup modal and clears invalid keys
- **API Key Errors**: Displays non-blocking banner for chat endpoints with key issues
- **Network Errors**: Shows toast notifications with error details
- **Provider Errors**: Graceful degradation when AI providers are not configured

### 3. Toast Notifications

Automatic user feedback for:
- Successful operations
- Error states
- Authentication issues
- Provider configuration warnings

### 4. Request Deduplication

Identical simultaneous requests are automatically deduplicated to prevent unnecessary network calls.

## Usage

### Basic API Calls

```javascript
import { apiClient } from './services/api-client.js';

// GET request
const data = await apiClient.fetchJson('/api/agents/status');

// POST request
const result = await apiClient.postJson('/api/agents/chat/agent_01', {
    message: 'Hello',
    model: 'openai/gpt-4'
});

// File upload
const formData = new FormData();
formData.append('file', file);
const response = await apiClient.fetch('/api/agents/upload/agent_01', {
    method: 'POST',
    body: formData
});
```

### Health Checks

```javascript
// Check API health
const isHealthy = await apiClient.checkApiHealth();

// Check provider configuration
const providerStatus = await apiClient.checkProviderConfiguration();
// Returns: { openrouter: boolean, openai: boolean, hasAnyProvider: boolean }
```

### Error Handling Examples

```javascript
try {
    const result = await apiClient.postJson('/api/agents/chat/agent_01', data);
    // Success - result contains response data
} catch (error) {
    // Error automatically handled with toast notification
    // Custom error handling if needed
    console.error('Operation failed:', error.message);
}
```

## Updated Components

### 1. API Service (`/static/js/services/api.js`)

All methods now use the centralized API client:

```javascript
export class AgentAPI {
    async sendMessage(agentId, message, model, enhancePrompt) {
        return apiClient.postJson(`${this.baseUrl}/chat/${agentId}`, {
            message, model, enhance_prompt: enhancePrompt 
        });
    }
}
```

### 2. Virtual Chat Integration

Updated to use API client for all requests:

```javascript
// Import API client dynamically
const { apiClient } = await import('./js/services/api-client.js');
const data = await apiClient.postJson(`/api/agents/chat/${agentId}`, {
    message, model, enhance_prompt: enhancePrompt 
});
```

### 3. App Initialization

Includes provider status checking and UI updates:

```javascript
// Check provider configuration and update UI accordingly
await this.checkProviderConfiguration();

// Set up periodic health checks
this.setupHealthChecks();
```

## API Key Management

### Setup Modal

The enhanced API key setup provides:
- Automatic detection of missing API keys
- Guided setup with server log instructions
- Skip option for development without auth
- Persistent storage and validation

### Warning Banner

Non-blocking banner appears when:
- API key is required but missing
- Authentication fails
- Chat endpoints return key errors

### Settings Integration

Users can:
- Update API keys through the warning banner
- Access setup modal from the "Open Settings" link
- Skip authentication for development

## Provider Configuration

### Status Checking

The system automatically checks:
- OpenRouter configuration status
- OpenAI configuration status
- Overall provider availability

### Graceful Degradation

When providers are not configured:
- Send buttons are disabled with helpful tooltips
- Model selectors show "(not configured)" for unavailable models
- Warning messages guide users to configure providers
- Chat interfaces show visual indicators of degraded state

### CSS Classes

Degraded states use CSS classes:
- `.provider-degraded` - Applied to affected elements
- Send buttons become disabled
- Visual indicators show configuration status

## Error States

### Authentication Errors (401)

1. Clear invalid API key from storage
2. Show API key setup modal
3. Display error toast notification
4. Prevent further requests until key is updated

### API Key Errors (Chat Endpoint)

1. Detect key-related errors in chat responses
2. Show non-blocking warning banner
3. Guide user to settings modal
4. Allow other operations to continue

### Network Errors

1. Show toast notification with error details
2. Log error for debugging
3. Don't interfere with UI state

### Provider Configuration Errors

1. Show provider warning banner
2. Update UI to indicate degraded state
3. Disable provider-dependent features
4. Guide user to configure environment variables

## Testing

Comprehensive test suite covers:
- Authentication header injection
- Error handling scenarios
- Request deduplication
- Health check functionality
- Provider configuration checking

Run tests:
```bash
npm test api-client.test.js
```

## Development Guidelines

### Adding New API Endpoints

Always use the centralized API client:

```javascript
// ✅ Good
const data = await apiClient.fetchJson('/api/new-endpoint');

// ❌ Avoid
const response = await fetch('/api/new-endpoint');
```

### Error Handling

Let the API client handle standard errors, add custom handling only when needed:

```javascript
try {
    const result = await apiClient.postJson('/api/endpoint', data);
    // Handle success
} catch (error) {
    // API client already showed toast notification
    // Add custom handling only if needed
    if (error.message.includes('specific-case')) {
        // Custom logic
    }
}
```

### UI State Management

Check provider status before enabling features:

```javascript
if (window.providerStatus?.hasAnyProvider) {
    // Enable AI-dependent features
} else {
    // Show degraded state or disable features
}
```

## Migration Guide

### From Direct Fetch Calls

Replace direct fetch calls:

```javascript
// Before
const response = await fetch('/api/endpoint', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
});
const result = await response.json();

// After
const result = await apiClient.postJson('/api/endpoint', data);
```

### From Manual Error Handling

Remove manual error handling where API client provides it:

```javascript
// Before
try {
    const response = await fetch('/api/endpoint');
    if (!response.ok) {
        showToast('Error occurred', 'error');
        throw new Error('Request failed');
    }
} catch (error) {
    showToast('Network error', 'error');
}

// After
try {
    const result = await apiClient.fetchJson('/api/endpoint');
    // Errors automatically handled
} catch (error) {
    // Only custom logic if needed
}
```

## Configuration

### Environment Variables

The system checks for these provider configurations:
- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`

### API Endpoints

Required endpoints for full functionality:
- `/api/health` - Health check
- `/api/providers/status` - Provider configuration status
- `/api/agents/chat/*` - Chat endpoints with key validation

## Troubleshooting

### API Key Issues

1. Check browser developer tools for 401 errors
2. Verify API key in localStorage: `localStorage.getItem('swarm_api_key')`
3. Check server logs for "Development API Key" message
4. Use the API key setup modal to update

### Provider Configuration

1. Check provider warning banner messages
2. Verify environment variables on server
3. Check `/api/providers/status` endpoint response
4. Look for degraded state visual indicators

### Network Issues

1. Check browser network tab for failed requests
2. Verify API client health checks: `window.apiHealthy`
3. Check toast notifications for error details
4. Verify server is running and accessible

## Future Enhancements

- **Retry Logic**: Automatic retry for transient failures
- **Request Caching**: Cache responses for performance
- **Offline Support**: Queue requests when offline
- **Rate Limiting**: Client-side rate limiting for API protection
- **Request Metrics**: Performance monitoring and analytics

