// API service module
import { getAuthHeaders } from '../config.js';

export class AgentAPI {
    constructor() {
        this.baseUrl = '/api/agents';
    }

    async sendMessage(agentId, message, model, enhancePrompt) {
        const response = await fetch(`${this.baseUrl}/chat/${agentId}`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ 
                message, 
                model, 
                enhance_prompt: enhancePrompt 
            })
        });
        return response.json();
    }

    async uploadFile(agentId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const headers = {};
        const authHeaders = getAuthHeaders();
        // Don't set Content-Type for FormData - browser will set it with boundary
        if (authHeaders['X-API-Key']) {
            headers['X-API-Key'] = authHeaders['X-API-Key'];
        }

        const response = await fetch(`${this.baseUrl}/upload/${agentId}`, {
            method: 'POST',
            headers: headers,
            body: formData
        });
        return response.json();
    }

    async getChatHistory(agentId) {
        const response = await fetch(`${this.baseUrl}/chat_history/${agentId}`, {
            headers: getAuthHeaders()
        });
        return response.json();
    }

    async clearChatHistory(agentId) {
        const response = await fetch(`${this.baseUrl}/chat_history/${agentId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        return response.ok;
    }

    async startCollaboration(taskDescription, taggedAgents, workingDirectory, sequential = false, enhancePrompt = true) {
        const response = await fetch(`${this.baseUrl}/collaborate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                task_description: taskDescription,
                tagged_agents: taggedAgents,
                working_directory: workingDirectory,
                sequential,
                enhance_prompt: enhancePrompt
            })
        });
        return response.json();
    }

    async getConversation(taskId) {
        const response = await fetch(`${this.baseUrl}/conversation/${taskId}`);
        if (!response.ok) {
            if (response.status === 404) {
                throw new Error('404: Task not found');
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    }

    async getWorkflowTemplates() {
        const response = await fetch(`${this.baseUrl}/workflows`);
        return response.json();
    }
}

export class FileAPI {
    async browseDirectory(path) {
        const response = await fetch(`/api/files/browse?path=${encodeURIComponent(path)}`);
        return response.json();
    }
}