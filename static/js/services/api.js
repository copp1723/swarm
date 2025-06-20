// API service module
import { apiClient } from './api-client.js';

export class AgentAPI {
    constructor() {
        this.baseUrl = '/api/agents';
    }

    async sendMessage(agentId, message, model, enhancePrompt) {
        return apiClient.postJson(`${this.baseUrl}/chat/${agentId}`, {
            message, 
            model, 
            enhance_prompt: enhancePrompt 
        });
    }

    async uploadFile(agentId, file) {
        const formData = new FormData();
        formData.append('file', file);

        // For file uploads, we don't set Content-Type header - let the browser handle it
        const response = await apiClient.fetch(`${this.baseUrl}/upload/${agentId}`, {
            method: 'POST',
            body: formData
            // No headers specified - API client will only add auth headers
        });
        return response.json();
    }

    async getChatHistory(agentId) {
        return apiClient.fetchJson(`${this.baseUrl}/chat_history/${agentId}`);
    }

    async clearChatHistory(agentId) {
        const response = await apiClient.delete(`${this.baseUrl}/chat_history/${agentId}`);
        return response.ok;
    }

    async startCollaboration(taskDescription, taggedAgents, workingDirectory, sequential = false, enhancePrompt = true) {
        return apiClient.postJson(`${this.baseUrl}/collaborate`, {
            task_description: taskDescription,
            tagged_agents: taggedAgents,
            working_directory: workingDirectory,
            sequential,
            enhance_prompt: enhancePrompt
        });
    }

    async getConversation(taskId) {
        try {
            return await apiClient.fetchJson(`${this.baseUrl}/conversation/${taskId}`);
        } catch (error) {
            if (error.message.includes('404')) {
                throw new Error('404: Task not found');
            }
            throw error;
        }
    }

    async getWorkflowTemplates() {
        return apiClient.fetchJson(`${this.baseUrl}/workflows`);
    }

    async getAgentStatus() {
        return apiClient.fetchJson(`${this.baseUrl}/status`);
    }

    async getProviderStatus() {
        return apiClient.fetchJson('/api/providers/status');
    }
}

export class FileAPI {
    async browseDirectory(path) {
        return apiClient.fetchJson(`/api/files/browse?path=${encodeURIComponent(path)}`);
    }
}
//# sourceMappingURL=api.js.map
