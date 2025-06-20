/**
 * Virtual Chat Integration
 * Integrates virtual scrolling with existing chat interface
 */

class VirtualChatManager {
    constructor() {
        this.virtualChats = new Map();
        this.isInitialized = false;
    }
    
    init() {
        if (this.isInitialized) return;
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initializeVirtualChats());
        } else {
            this.initializeVirtualChats();
        }
        
        this.isInitialized = true;
    }
    
    initializeVirtualChats() {
        // Find all agent chat areas and convert them to virtual chats
        const agentIds = window.agents ? window.agents.map(agent => agent.id) : [];
        
        agentIds.forEach(agentId => {
            this.createVirtualChatForAgent(agentId);
        });
        
        console.log('Virtual chat containers initialized for agents:', agentIds);
    }
    
    createVirtualChatForAgent(agentId) {
        const chatContainer = document.getElementById(`chat-${agentId}`);
        if (!chatContainer) {
            console.warn(`Chat container not found for agent: ${agentId}`);
            return;
        }
        
        // Extract existing messages before virtualizing
        const existingMessages = this.extractExistingMessages(chatContainer);
        
        // Create virtual chat container
        const virtualChat = new VirtualChatContainer(`chat-${agentId}`, {
            itemHeight: 120, // Average message height
            overscan: 3,
            scrollThreshold: 100,
            maxMessages: 5000 // Keep 5000 messages per agent
        });
        
        // Store reference
        this.virtualChats.set(agentId, virtualChat);
        
        // Add existing messages to virtual chat
        if (existingMessages.length > 0) {
            virtualChat.addMessages(existingMessages);
        }
        
        // Set up message interception
        this.interceptMessageFunctions(agentId, virtualChat);
        
        console.log(`Virtual chat created for ${agentId} with ${existingMessages.length} existing messages`);
    }
    
    extractExistingMessages(chatContainer) {
        const messages = [];
        const messageElements = chatContainer.querySelectorAll('.chat-message');
        
        messageElements.forEach((el, index) => {
            try {
                const isUser = el.classList.contains('justify-end') || el.querySelector('.bg-blue-600');
                const content = this.extractMessageContent(el, isUser);
                
                if (content) {
                    messages.push({
                        id: `existing_${index}_${Date.now()}`,
                        type: isUser ? 'user' : 'agent',
                        content: content,
                        agentName: isUser ? 'You' : this.extractAgentName(el),
                        timestamp: new Date().toISOString(),
                        enhanced: el.querySelector('.bg-blue-100') !== null
                    });
                }
            } catch (error) {
                console.warn('Error extracting message:', error);
            }
        });
        
        return messages;
    }
    
    extractMessageContent(element, isUser) {
        try {
            if (isUser) {
                // User message - extract from blue bubble
                const bubble = element.querySelector('.bg-blue-600') || element.querySelector('.max-w-\\[80%\\]');
                return bubble ? bubble.textContent.trim() : '';
            } else {
                // Agent message - extract from response area
                const responseArea = element.querySelector('.agent-response') || 
                                   element.querySelector('.bg-gray-100') ||
                                   element.querySelector('.max-w-\\[80%\\]');
                return responseArea ? responseArea.innerHTML : '';
            }
        } catch (error) {
            console.warn('Error extracting content:', error);
            return '';
        }
    }
    
    extractAgentName(element) {
        try {
            const nameElement = element.querySelector('.text-gray-600') || 
                              element.querySelector('.font-medium');
            return nameElement ? nameElement.textContent.trim() : 'Assistant';
        } catch (error) {
            return 'Assistant';
        }
    }
    
    interceptMessageFunctions(agentId, virtualChat) {
        // Store original functions if they exist
        const originalSendMessage = window.sendMessage;
        const originalSendMessageButton = window.sendMessageButton;
        
        // Override sendMessage function for this agent
        if (originalSendMessage) {
            window[`sendMessage_${agentId}`] = async function(event, targetAgentId) {
                if (targetAgentId !== agentId) {
                    return originalSendMessage.call(this, event, targetAgentId);
                }
                
                if (event.key === 'Enter') {
                    const input = document.getElementById(`input-${agentId}`);
                    let message = input.value.trim();
                    
                    // Add directory context if selected
                    const directory = window.agentDirectories ? window.agentDirectories[agentId] : null;
                    if (directory && !message.includes('[Working in:')) {
                        message = `[Working in: ${directory}]\n${message}`;
                    }
                    if (!message) return;
                    
                    const model = document.querySelector(`.model-selector[data-agent="${agentId}"]`)?.value || 'openai/gpt-4';
                    input.value = '';
                    
                    // Add user message to virtual chat
                    virtualChat.addMessage({
                        type: 'user',
                        content: message,
                        agentName: 'You'
                    });
                    
                    // Update agent status
                    if (window.updateAgentStatus) {
                        window.updateAgentStatus(agentId, true);
                    }
                    
                    // Add typing indicator
                    const typingMessageId = `typing_${Date.now()}`;
                    virtualChat.addMessage({
                        id: typingMessageId,
                        type: 'agent',
                        content: 'Typing...',
                        agentName: window.getAgentName ? window.getAgentName(agentId) : 'Assistant',
                        isTyping: true
                    });
                    
                    try {
                        const enhancePrompt = document.getElementById('enhance-prompt-global')?.checked || false;
                        
                        // Import API client dynamically
                        const { apiClient } = await import('./js/services/api-client.js');
                        const data = await apiClient.postJson(`/api/agents/chat/${agentId}`, {
                            message, 
                            model, 
                            enhance_prompt: enhancePrompt 
                        });
                        
                        // Remove typing indicator
                        virtualChat.removeMessage(typingMessageId);
                        
                        if (data.success) {
                            // Add agent response
                            virtualChat.addMessage({
                                type: 'agent',
                                content: data.response,
                                agentName: window.getAgentName ? window.getAgentName(agentId) : 'Assistant',
                                enhanced: data.enhanced || false
                            });
                        } else {
                            // Add error message
                            virtualChat.addMessage({
                                type: 'agent',
                                content: `Error: ${data.error}`,
                                agentName: 'System',
                                isError: true
                            });
                        }
                    } catch (err) {
                        // Remove typing indicator on error
                        virtualChat.removeMessage(typingMessageId);
                        
                        virtualChat.addMessage({
                            type: 'agent',
                            content: 'Failed to send message',
                            agentName: 'System',
                            isError: true
                        });
                    } finally {
                        if (window.updateAgentStatus) {
                            window.updateAgentStatus(agentId, false);
                        }
                    }
                }
            };
        }
        
        // Override button send function
        if (originalSendMessageButton) {
            window[`sendMessageButton_${agentId}`] = function(targetAgentId) {
                if (targetAgentId !== agentId) {
                    return originalSendMessageButton.call(this, targetAgentId);
                }
                
                const input = document.getElementById(`input-${targetAgentId}`);
                const event = { key: 'Enter' };
                window[`sendMessage_${agentId}`](event, agentId);
            };
        }
    }
    
    // Public API methods
    getVirtualChat(agentId) {
        return this.virtualChats.get(agentId);
    }
    
    addMessageToAgent(agentId, message) {
        const virtualChat = this.virtualChats.get(agentId);
        if (virtualChat) {
            virtualChat.addMessage(message);
        }
    }
    
    clearAgentChat(agentId) {
        const virtualChat = this.virtualChats.get(agentId);
        if (virtualChat) {
            virtualChat.clearMessages();
        }
    }
    
    scrollToBottomForAgent(agentId) {
        const virtualChat = this.virtualChats.get(agentId);
        if (virtualChat) {
            virtualChat.scrollToBottom();
        }
    }
    
    getAgentMessageCount(agentId) {
        const virtualChat = this.virtualChats.get(agentId);
        return virtualChat ? virtualChat.getMessageCount() : 0;
    }
    
    // Performance monitoring
    getPerformanceStats() {
        const stats = {
            totalAgents: this.virtualChats.size,
            totalMessages: 0,
            memoryUsage: 0
        };
        
        this.virtualChats.forEach((virtualChat, agentId) => {
            const chatStats = virtualChat.getPerformanceStats();
            stats.totalMessages += chatStats.totalMessages;
            stats.memoryUsage += chatStats.memoryUsage.messages + chatStats.memoryUsage.heightCache;
            stats[agentId] = chatStats;
        });
        
        return stats;
    }
    
    // Load chat history for specific agent
    async loadChatHistory(agentId) {
        const virtualChat = this.virtualChats.get(agentId);
        if (!virtualChat) return;
        
        try {
            // Import API client dynamically
            const { apiClient } = await import('./js/services/api-client.js');
            const data = await apiClient.fetchJson(`/api/agents/chat_history/${agentId}`);
            
            if (data.success && data.history && data.history.length > 0) {
                // Clear existing messages
                virtualChat.clearMessages();
                
                // Convert history to virtual chat messages
                const messages = data.history.map((msg, index) => ({
                    id: `history_${index}_${Date.now()}`,
                    type: msg.role === 'user' ? 'user' : 'agent',
                    content: msg.content,
                    agentName: msg.role === 'user' ? 'You' : (window.getAgentName ? window.getAgentName(agentId) : 'Assistant'),
                    timestamp: new Date().toISOString()
                }));
                
                virtualChat.addMessages(messages);
                
                console.log(`Loaded ${messages.length} messages for ${agentId}`);
            }
        } catch (err) {
            console.error(`Error loading chat history for ${agentId}:`, err);
        }
    }
    
    // Clean up all virtual chats
    destroy() {
        this.virtualChats.forEach((virtualChat) => {
            virtualChat.destroy();
        });
        this.virtualChats.clear();
        this.isInitialized = false;
    }
}

// Create global virtual chat manager
window.virtualChatManager = new VirtualChatManager();

// Enhanced message formatting for virtual chat
if (!window.formatAgentResponse) {
    window.formatAgentResponse = function(text) {
        // Create a temporary div to safely escape HTML first
        const tempDiv = document.createElement('div');
        tempDiv.textContent = text;
        let formatted = tempDiv.innerHTML;
        
        // Apply formatting (same as original but with proper escaping)
        formatted = formatted.replace(/^###\\s+(.+)$/gm, '<h3 class="font-bold text-lg text-gray-900 mt-6 mb-3 border-b-2 border-blue-200 pb-2">$1</h3>');
        formatted = formatted.replace(/^##\\s+(.+)$/gm, '<h4 class="font-semibold text-base text-gray-800 mt-3 mb-2">$1</h4>');
        formatted = formatted.replace(/^(\\d+)\\.\\s+(.+)$/gm, '<li class="ml-6 mb-2"><span class="font-semibold text-blue-600">$1.</span> $2</li>');
        formatted = formatted.replace(/^[-*]\\s+(.+)$/gm, '<li class="ml-6 mb-1">• $1</li>');
        formatted = formatted.replace(/(<li class="ml-6[^"]*">.+<\/li>\n?)+/g, function(match) {
            return '<ul class="list-none space-y-1 my-3 bg-gray-50 p-3 rounded-lg border-l-3 border-blue-400">' + match + '</ul>';
        });
        formatted = formatted.replace(/```(\\w+)?\\n?([^`]+)```/g, function(match, lang, code) {
            const language = lang || 'plaintext';
            return `<div class="my-3">
                <div class="bg-gray-700 text-gray-300 px-3 py-1 text-xs rounded-t-lg">${language}</div>
                <pre class="bg-gray-800 text-gray-100 p-4 rounded-b-lg overflow-x-auto"><code>${code.trim()}</code></pre>
            </div>`;
        });
        formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-gray-200 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800">$1</code>');
        formatted = formatted.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');
        formatted = formatted.replace(/\\n/g, '<br>');
        
        return formatted;
    };
}

// Override original functions to work with virtual chat
function enhanceOriginalFunctions() {
    // Store original functions
    const originalSendMessage = window.sendMessage;
    const originalSendMessageButton = window.sendMessageButton;
    const originalClearChat = window.clearChat;
    const originalLoadChatHistory = window.loadChatHistory;
    
    // Enhanced sendMessage that works with virtual chat
    if (originalSendMessage) {
        window.sendMessage = function(event, agentId) {
            const virtualChat = window.virtualChatManager.getVirtualChat(agentId);
            if (virtualChat) {
                // Use virtual chat enhanced function
                const enhancedFunction = window[`sendMessage_${agentId}`];
                if (enhancedFunction) {
                    return enhancedFunction.call(this, event, agentId);
                }
            }
            // Fallback to original
            return originalSendMessage.call(this, event, agentId);
        };
    }
    
    // Enhanced sendMessageButton
    if (originalSendMessageButton) {
        window.sendMessageButton = function(agentId) {
            const virtualChat = window.virtualChatManager.getVirtualChat(agentId);
            if (virtualChat) {
                const enhancedFunction = window[`sendMessageButton_${agentId}`];
                if (enhancedFunction) {
                    return enhancedFunction.call(this, agentId);
                }
            }
            return originalSendMessageButton.call(this, agentId);
        };
    }
    
    // Enhanced clearChat
    if (originalClearChat) {
        window.clearChat = async function(agentId) {
            // Clear virtual chat
            window.virtualChatManager.clearAgentChat(agentId);
            
            // Call original API
            return originalClearChat.call(this, agentId);
        };
    }
    
    // Enhanced loadChatHistory
    if (originalLoadChatHistory) {
        window.loadChatHistory = async function(agentId) {
            // Use virtual chat loader
            return window.virtualChatManager.loadChatHistory(agentId);
        };
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for the original interface to initialize
    setTimeout(() => {
        window.virtualChatManager.init();
        enhanceOriginalFunctions();
        
        // Add performance monitoring to window
        window.getChatPerformanceStats = () => window.virtualChatManager.getPerformanceStats();
        
        console.log('Virtual chat system initialized successfully');
    }, 500);
});

// Debug utilities
window.debugVirtualChat = {
    getStats: () => window.virtualChatManager.getPerformanceStats(),
    getChat: (agentId) => window.virtualChatManager.getVirtualChat(agentId),
    scrollToBottom: (agentId) => window.virtualChatManager.scrollToBottomForAgent(agentId),
    addTestMessages: (agentId, count = 100) => {
        const virtualChat = window.virtualChatManager.getVirtualChat(agentId);
        if (virtualChat) {
            for (let i = 0; i < count; i++) {
                virtualChat.addMessage({
                    type: i % 2 === 0 ? 'user' : 'agent',
                    content: `Test message ${i + 1}. This is a longer message to test the virtual scrolling performance with varied message lengths. Lorem ipsum dolor sit amet, consectetur adipiscing elit.`,
                    agentName: i % 2 === 0 ? 'You' : 'Assistant'
                });
            }
        }
    }
};
//# sourceMappingURL=virtual-chat-integration.js.map
