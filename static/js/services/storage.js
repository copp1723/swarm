// Storage service for managing local data
export class StorageService {
    constructor() {
        this.prefix = 'swarm_';
    }

    // Agent directories
    getAgentDirectory(agentId) {
        return localStorage.getItem(`${this.prefix}agent_dir_${agentId}`) || null;
    }

    setAgentDirectory(agentId, directory) {
        localStorage.setItem(`${this.prefix}agent_dir_${agentId}`, directory);
    }

    // Chat history cache
    getChatHistoryCache(agentId) {
        const cached = localStorage.getItem(`${this.prefix}chat_cache_${agentId}`);
        if (cached) {
            try {
                return JSON.parse(cached);
            } catch (e) {
                return null;
            }
        }
        return null;
    }

    setChatHistoryCache(agentId, history) {
        try {
            localStorage.setItem(`${this.prefix}chat_cache_${agentId}`, JSON.stringify(history));
        } catch (e) {
            console.error('Failed to cache chat history:', e);
        }
    }

    // Model preferences
    getModelPreference(agentId) {
        return localStorage.getItem(`${this.prefix}model_${agentId}`) || 'openai/gpt-4.1';
    }

    setModelPreference(agentId, model) {
        localStorage.setItem(`${this.prefix}model_${agentId}`, model);
    }

    // Global settings
    getEnhancePromptSetting() {
        return localStorage.getItem(`${this.prefix}enhance_prompt`) !== 'false';
    }

    setEnhancePromptSetting(value) {
        localStorage.setItem(`${this.prefix}enhance_prompt`, value.toString());
    }

    // Clear all storage
    clearAll() {
        const keys = Object.keys(localStorage);
        keys.forEach(key => {
            if (key.startsWith(this.prefix)) {
                localStorage.removeItem(key);
            }
        });
    }
}
//# sourceMappingURL=storage.js.map
