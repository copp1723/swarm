/**
 * Memory UI Component for Agent Interface
 * Provides visual feedback for memory operations
 */

class MemoryUI {
    constructor() {
        this.memoryEnabled = true;
        this.memoryIndicators = new Map();
    }

    /**
     * Add memory indicator to agent chat
     */
    addMemoryIndicator(agentId) {
        const chatHeader = document.querySelector(`#chat-container-${agentId} .chat-header`);
        if (!chatHeader || this.memoryIndicators.has(agentId)) return;

        const indicator = document.createElement('div');
        indicator.className = 'memory-indicator';
        indicator.id = `memory-indicator-${agentId}`;
        indicator.innerHTML = `
            <div class="flex items-center space-x-2 text-xs">
                <i data-lucide="brain" class="w-4 h-4 text-purple-500"></i>
                <span class="text-gray-600">Memory: <span class="memory-status">Active</span></span>
                <button onclick="memoryUI.showAgentMemories('${agentId}')" 
                        class="ml-2 text-purple-600 hover:text-purple-700 underline">
                    View Memories
                </button>
            </div>
        `;

        chatHeader.appendChild(indicator);
        this.memoryIndicators.set(agentId, indicator);
        lucide.createIcons();
    }

    /**
     * Search memories
     */
    async searchMemories(query, agentId = null) {
        try {
            const response = await fetch('/api/memory/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, agent_id: agentId, limit: 10 })
            });

            const data = await response.json();
            if (data.success) {
                return data.memories;
            }
            return [];
        } catch (error) {
            console.error('Error searching memories:', error);
            return [];
        }
    }

    /**
     * Add a memory
     */
    async addMemory(content, agentId, metadata = {}) {
        try {
            const response = await fetch('/api/memory/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content,
                    agent_id: agentId,
                    metadata: {
                        ...metadata,
                        added_via: 'ui',
                        timestamp: new Date().toISOString()
                    }
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showMemoryNotification('Memory added successfully', 'success');
                return data;
            }
            throw new Error(data.error || 'Failed to add memory');
        } catch (error) {
            console.error('Error adding memory:', error);
            this.showMemoryNotification('Failed to add memory', 'error');
            return null;
        }
    }

    /**
     * Show agent memories in a modal
     */
    async showAgentMemories(agentId) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-4xl w-full max-h-[80vh] overflow-hidden">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-xl font-semibold flex items-center space-x-2">
                        <i data-lucide="brain" class="w-6 h-6 text-purple-500"></i>
                        <span>${getAgentName(agentId)} Memories</span>
                    </h3>
                    <button onclick="this.closest('.fixed').remove()" class="text-gray-500 hover:text-gray-700">
                        <i data-lucide="x" class="w-6 h-6"></i>
                    </button>
                </div>
                
                <!-- Search bar -->
                <div class="mb-4">
                    <input type="text" 
                           id="memory-search-${agentId}" 
                           placeholder="Search memories..."
                           class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                           onkeyup="memoryUI.searchAgentMemories('${agentId}', event)">
                </div>
                
                <!-- Memory list -->
                <div id="memory-list-${agentId}" class="overflow-y-auto max-h-[60vh] space-y-3">
                    <div class="text-center text-gray-500">
                        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div>
                        <p class="mt-2">Loading memories...</p>
                    </div>
                </div>
                
                <!-- Add memory button -->
                <div class="mt-4 pt-4 border-t">
                    <button onclick="memoryUI.showAddMemoryForm('${agentId}')" 
                            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                        <i data-lucide="plus" class="w-4 h-4 inline mr-2"></i>
                        Add Memory
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        lucide.createIcons();

        // Load memories
        await this.loadAgentMemories(agentId);
    }

    /**
     * Load and display agent memories
     */
    async loadAgentMemories(agentId) {
        try {
            const response = await fetch(`/api/memory/agent/${agentId}?limit=50`);
            const data = await response.json();

            const listContainer = document.getElementById(`memory-list-${agentId}`);
            if (!listContainer) return;

            if (data.success && data.memories && data.memories.length > 0) {
                listContainer.innerHTML = data.memories.map(memory => `
                    <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow">
                        <div class="text-sm text-gray-800 mb-2">${this.escapeHtml(memory.content)}</div>
                        <div class="flex items-center justify-between text-xs text-gray-500">
                            <span>${new Date(memory.metadata?.timestamp || memory.timestamp).toLocaleString()}</span>
                            ${memory.score ? `<span class="text-purple-600">Score: ${memory.score.toFixed(2)}</span>` : ''}
                        </div>
                        ${memory.metadata ? `
                        <div class="mt-2 text-xs text-gray-600">
                            ${Object.entries(memory.metadata)
                                .filter(([key]) => !['timestamp', 'agent_id'].includes(key))
                                .map(([key, value]) => `<span class="mr-2">${key}: ${value}</span>`)
                                .join('')}
                        </div>
                        ` : ''}
                    </div>
                `).join('');
            } else {
                listContainer.innerHTML = `
                    <div class="text-center text-gray-500 py-8">
                        <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-3 text-gray-300"></i>
                        <p>No memories found for this agent</p>
                    </div>
                `;
            }

            lucide.createIcons();
        } catch (error) {
            console.error('Error loading memories:', error);
            const listContainer = document.getElementById(`memory-list-${agentId}`);
            if (listContainer) {
                listContainer.innerHTML = `
                    <div class="text-center text-red-500 py-8">
                        <i data-lucide="alert-circle" class="w-12 h-12 mx-auto mb-3"></i>
                        <p>Error loading memories</p>
                    </div>
                `;
                lucide.createIcons();
            }
        }
    }

    /**
     * Search agent memories
     */
    async searchAgentMemories(agentId, event) {
        const query = event.target.value.trim();
        if (!query) {
            await this.loadAgentMemories(agentId);
            return;
        }

        if (event.key !== 'Enter') return;

        const listContainer = document.getElementById(`memory-list-${agentId}`);
        listContainer.innerHTML = '<div class="text-center text-gray-500"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto"></div></div>';

        const memories = await this.searchMemories(query, agentId);
        
        if (memories.length > 0) {
            listContainer.innerHTML = memories.map(memory => `
                <div class="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-md transition-shadow">
                    <div class="text-sm text-gray-800 mb-2">${this.escapeHtml(memory.content)}</div>
                    <div class="flex items-center justify-between text-xs text-gray-500">
                        <span>Relevance: ${(memory.score * 100).toFixed(0)}%</span>
                    </div>
                </div>
            `).join('');
        } else {
            listContainer.innerHTML = '<div class="text-center text-gray-500 py-8">No matching memories found</div>';
        }
    }

    /**
     * Show add memory form
     */
    showAddMemoryForm(agentId) {
        const formModal = document.createElement('div');
        formModal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-60';
        formModal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full">
                <h4 class="text-lg font-semibold mb-4">Add Memory for ${getAgentName(agentId)}</h4>
                <textarea id="new-memory-content" 
                          class="w-full h-32 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                          placeholder="Enter memory content..."></textarea>
                <div class="mt-4 flex justify-end space-x-2">
                    <button onclick="this.closest('.fixed').remove()" 
                            class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                        Cancel
                    </button>
                    <button onclick="memoryUI.saveNewMemory('${agentId}')" 
                            class="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
                        Save Memory
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(formModal);
        document.getElementById('new-memory-content').focus();
    }

    /**
     * Save new memory
     */
    async saveNewMemory(agentId) {
        const content = document.getElementById('new-memory-content').value.trim();
        if (!content) {
            this.showMemoryNotification('Please enter memory content', 'warning');
            return;
        }

        const result = await this.addMemory(content, agentId);
        if (result) {
            document.querySelector('.fixed.z-60').remove(); // Close form
            await this.loadAgentMemories(agentId); // Refresh list
        }
    }

    /**
     * Show memory notification
     */
    showMemoryNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed bottom-4 right-4 p-4 rounded-lg shadow-lg z-50 animate-slide-in ${
            type === 'error' ? 'bg-red-500 text-white' : 
            type === 'success' ? 'bg-green-500 text-white' : 
            type === 'warning' ? 'bg-yellow-500 text-white' : 
            'bg-purple-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <i data-lucide="brain" class="w-5 h-5"></i>
                <span>${message}</span>
            </div>
        `;
        document.body.appendChild(notification);
        lucide.createIcons();
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Initialize memory UI for all agents
     */
    initialize() {
        // Add memory indicators to all agent chats
        if (typeof agents !== 'undefined') {
            agents.forEach(agent => {
                this.addMemoryIndicator(agent.id);
            });
        }

        // Add global memory status
        this.addGlobalMemoryStatus();
    }

    /**
     * Add global memory status indicator
     */
    addGlobalMemoryStatus() {
        const header = document.querySelector('.main-header');
        if (!header) return;

        const statusDiv = document.createElement('div');
        statusDiv.className = 'flex items-center space-x-2 text-sm';
        statusDiv.innerHTML = `
            <i data-lucide="brain" class="w-4 h-4 text-purple-500"></i>
            <span class="text-gray-600">Supermemory</span>
            <span class="px-2 py-1 text-xs bg-green-100 text-green-700 rounded-full">Connected</span>
        `;

        header.appendChild(statusDiv);
        lucide.createIcons();
    }
}

// Create global instance
const memoryUI = new MemoryUI();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    memoryUI.initialize();
});