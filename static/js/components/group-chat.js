// Group Chat Component for Multi-Agent Conversations
import { createElement, escapeHtml, showNotification } from '../utils/dom-helpers.js';
import { formatAgentResponse } from '../utils/formatters.js';
import { AgentAPI } from '../services/api.js';

export class GroupChat {
    constructor(agents, initialMessage, workingDirectory) {
        this.agents = agents; // Array of agent objects
        this.messages = [];
        this.workingDirectory = workingDirectory;
        this.api = new AgentAPI();
        this.chatId = `group_${Date.now()}`;
        this.isMinimized = false;
        this.container = null;
        
        // Create and show the group chat window
        this.create(initialMessage);
    }
    
    create(initialMessage) {
        // Create the floating group chat window
        this.container = createElement('div', 'group-chat-window');
        this.container.style.zIndex = '9999'; // Ensure it's on top
        this.container.innerHTML = `
            <div class="group-chat-header">
                <div class="group-chat-title">
                    <i data-lucide="users" class="w-4 h-4"></i>
                    <span>Group Chat: ${this.agents.map(a => a.name).join(', ')}</span>
                </div>
                <div class="group-chat-controls">
                    <button class="minimize-btn" title="Minimize">
                        <i data-lucide="minus" class="w-4 h-4"></i>
                    </button>
                    <button class="close-btn" title="Close">
                        <i data-lucide="x" class="w-4 h-4"></i>
                    </button>
                </div>
            </div>
            
            <div class="group-chat-body">
                <div class="group-chat-messages" id="group-messages-${this.chatId}">
                    <!-- Messages will appear here -->
                </div>
                
                <div class="group-chat-input-area">
                    ${this.workingDirectory ? `
                        <div class="working-directory-indicator">
                            <i data-lucide="folder" class="w-3 h-3"></i>
                            <span>${this.workingDirectory}</span>
                        </div>
                    ` : ''}
                    <div class="group-chat-input-wrapper">
                        <input type="text" 
                               class="group-chat-input" 
                               id="group-input-${this.chatId}"
                               placeholder="Type your message to all agents...">
                        <button class="group-chat-send" id="group-send-${this.chatId}">
                            <i data-lucide="send" class="w-4 h-4"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add styles if not already present
        this.addStyles();
        
        // Append to body
        document.body.appendChild(this.container);
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Update icons
        if (window.updateIcons) window.updateIcons();
        
        // Add initial message if provided
        if (initialMessage) {
            this.addMessage('user', 'You', initialMessage);
            // Automatically send the initial message to start the collaboration
            this.sendInitialMessage(initialMessage);
        }
        
        // Focus the input
        const input = document.getElementById(`group-input-${this.chatId}`);
        if (input) input.focus();
        
        // Hide the main chat interface and show group chat prominently
        this.takeFocus();
        
        // Announce group chat creation
        showNotification(`Group chat started with ${this.agents.map(a => a.name).join(', ')}`, 'success');
    }
    
    setupEventListeners() {
        // Close button
        this.container.querySelector('.close-btn').addEventListener('click', () => this.close());
        
        // Minimize button
        this.container.querySelector('.minimize-btn').addEventListener('click', () => this.toggleMinimize());
        
        // Send button
        const sendBtn = document.getElementById(`group-send-${this.chatId}`);
        const input = document.getElementById(`group-input-${this.chatId}`);
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        
        // Make the window draggable
        this.makeDraggable();
    }
    
    makeDraggable() {
        const header = this.container.querySelector('.group-chat-header');
        let isDragging = false;
        let currentX;
        let currentY;
        let initialX;
        let initialY;
        let xOffset = 0;
        let yOffset = 0;
        
        header.addEventListener('mousedown', (e) => {
            if (e.target.closest('.group-chat-controls')) return;
            
            initialX = e.clientX - xOffset;
            initialY = e.clientY - yOffset;
            isDragging = true;
            header.style.cursor = 'grabbing';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            
            e.preventDefault();
            currentX = e.clientX - initialX;
            currentY = e.clientY - initialY;
            xOffset = currentX;
            yOffset = currentY;
            
            this.container.style.transform = `translate(${currentX}px, ${currentY}px)`;
        });
        
        document.addEventListener('mouseup', () => {
            isDragging = false;
            header.style.cursor = 'grab';
        });
    }
    
    async sendInitialMessage(message) {
        // Create collaborative task for the initial message
        try {
            const taggedAgents = this.agents.map(agent => agent.id);
            
            const response = await this.api.startCollaboration(
                message,
                taggedAgents,
                this.workingDirectory || '/Users/copp1723/Desktop/swarm/mcp_new_project',
                false, // parallel execution
                true   // enhance prompt
            );
            
            if (response.success) {
                this.taskId = response.task_id;
                this.addMessage('system', 'System', `Processing your request...`);
                this.startPollingForUpdates();
            } else {
                this.addMessage('error', 'System', 'Failed to start collaborative task');
            }
        } catch (error) {
            console.error('Error sending initial message:', error);
            this.addMessage('error', 'System', 'Error: ' + error.message);
        }
    }
    
    async sendMessage() {
        const input = document.getElementById(`group-input-${this.chatId}`);
        const message = input.value.trim();
        if (!message) return;
        
        input.value = '';
        
        // Add user message
        this.addMessage('user', 'You', message);
        
        // Create collaborative task
        try {
            const taggedAgents = this.agents.map(agent => agent.id);
            
            const response = await this.api.startCollaboration(
                message,
                taggedAgents,
                this.workingDirectory || '/Users/copp1723/Desktop/swarm/mcp_new_project',
                false, // parallel execution
                true   // enhance prompt
            );
            
            if (response.success) {
                this.taskId = response.task_id;
                this.addMessage('system', 'System', `Processing your request...`);
                this.startPollingForUpdates();
            } else {
                this.addMessage('error', 'System', 'Failed to start collaborative task');
            }
        } catch (error) {
            console.error('Error sending group message:', error);
            this.addMessage('error', 'System', 'Error: ' + error.message);
        }
    }
    
    async startPollingForUpdates() {
        if (!this.taskId) return;
        
        let pollCount = 0;
        const maxPolls = 60; // Poll for up to 2 minutes
        
        const pollInterval = setInterval(async () => {
            pollCount++;
            
            try {
                const response = await this.api.getConversation(this.taskId);
                console.log('Group chat poll response:', response);
                
                if (response.success) {
                    // Process all communications
                    const allCommunications = response.all_communications || [];
                    
                    allCommunications.forEach(comm => {
                        if (!this.messages.find(m => m.id === comm.message_id)) {
                            this.addMessage(
                                'agent',
                                comm.from_agent,
                                comm.message,
                                comm.message_id
                            );
                            
                            if (comm.response) {
                                this.addMessage(
                                    'agent',
                                    comm.to_agent,
                                    comm.response,
                                    comm.message_id + '_response'
                                );
                            }
                        }
                    });
                    
                    // Process conversations
                    if (response.conversations && response.conversations.length > 0) {
                        response.conversations.forEach(conv => {
                            const msgId = `conv_${conv.agent_id}_${new Date(conv.timestamp).getTime()}`;
                            if (!this.messages.find(m => m.id === msgId)) {
                                this.addMessage(
                                    'agent',
                                    conv.agent_id,
                                    conv.content,
                                    msgId
                                );
                            }
                        });
                    }
                    
                    // Check if task is complete
                    if (response.status === 'completed' || pollCount >= maxPolls) {
                        clearInterval(pollInterval);
                        if (response.status === 'completed') {
                            this.addMessage('system', 'System', 'Collaboration completed successfully!');
                        } else {
                            this.addMessage('system', 'System', 'Task is taking longer than expected. You can continue typing to interact.');
                        }
                    }
                } else {
                    // Handle error responses
                    if (response.error && response.error.includes('not found')) {
                        // Task not found - stop polling
                        clearInterval(pollInterval);
                        this.addMessage('error', 'System', 'Task no longer exists. It may have been cleared after a server restart.');
                        // Clear the task ID to prevent further polling
                        this.taskId = null;
                    }
                }
            } catch (error) {
                console.error('Error polling for updates:', error);
                if (pollCount >= 5) {
                    clearInterval(pollInterval);
                    this.addMessage('error', 'System', 'Unable to get updates. Please check your connection.');
                }
            }
        }, 2000); // Poll every 2 seconds
        
        // Store interval ID for cleanup
        this.pollInterval = pollInterval;
    }
    
    addMessage(type, sender, content, messageId = null) {
        const message = {
            id: messageId || `msg_${Date.now()}_${Math.random()}`,
            type,
            sender,
            content,
            timestamp: new Date()
        };
        
        this.messages.push(message);
        
        const messagesContainer = document.getElementById(`group-messages-${this.chatId}`);
        if (!messagesContainer) return;
        
        const messageEl = createElement('div', `group-message ${type}-message`);
        
        if (type === 'user') {
            messageEl.innerHTML = `
                <div class="message-sender">You</div>
                <div class="message-content user-content">${escapeHtml(content)}</div>
            `;
        } else if (type === 'agent') {
            const agentInfo = this.agents.find(a => a.id === sender) || { name: sender, color: 'gray' };
            messageEl.innerHTML = `
                <div class="message-sender" style="color: var(--color-${agentInfo.color}-600)">${agentInfo.name}</div>
                <div class="message-content agent-content">${formatAgentResponse(content)}</div>
            `;
        } else if (type === 'system') {
            messageEl.innerHTML = `
                <div class="message-content system-content">${content}</div>
            `;
        } else if (type === 'error') {
            messageEl.innerHTML = `
                <div class="message-content error-content">${content}</div>
            `;
        }
        
        messagesContainer.appendChild(messageEl);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    toggleMinimize() {
        this.isMinimized = !this.isMinimized;
        this.container.classList.toggle('minimized', this.isMinimized);
        
        const icon = this.container.querySelector('.minimize-btn i');
        icon.setAttribute('data-lucide', this.isMinimized ? 'maximize-2' : 'minus');
        if (window.updateIcons) window.updateIcons();
    }
    
    close() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        this.container.remove();
        
        // Show the main content again
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.display = '';
        }
        
        showNotification('Group chat closed', 'info');
    }
    
    takeFocus() {
        // Hide the main chat interface
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.style.display = 'none';
        }
        
        // Make the group chat window full-screen
        this.container.style.position = 'fixed';
        this.container.style.top = '50%';
        this.container.style.left = '50%';
        this.container.style.transform = 'translate(-50%, -50%)';
        this.container.style.width = '90%';
        this.container.style.maxWidth = '1200px';
        this.container.style.height = '85vh';
    }
    
    addStyles() {
        if (document.getElementById('group-chat-styles')) return;
        
        const styles = document.createElement('style');
        styles.id = 'group-chat-styles';
        styles.textContent = `
            .group-chat-window {
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 500px;
                height: 600px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
                display: flex;
                flex-direction: column;
                z-index: 9999;
                transition: all 0.3s ease;
            }
            
            .group-chat-window.minimized {
                height: 50px;
            }
            
            .group-chat-window.minimized .group-chat-body {
                display: none;
            }
            
            .group-chat-header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 15px;
                border-radius: 12px 12px 0 0;
                display: flex;
                justify-content: space-between;
                align-items: center;
                cursor: grab;
                user-select: none;
            }
            
            .group-chat-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-weight: 600;
            }
            
            .group-chat-controls {
                display: flex;
                gap: 8px;
            }
            
            .group-chat-controls button {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                color: white;
                width: 30px;
                height: 30px;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .group-chat-controls button:hover {
                background: rgba(255, 255, 255, 0.3);
            }
            
            .group-chat-body {
                flex: 1;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .group-chat-messages {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
                background: #f9fafb;
            }
            
            .group-message {
                margin-bottom: 15px;
                animation: slideIn 0.3s ease;
            }
            
            @keyframes slideIn {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .message-sender {
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 4px;
            }
            
            .message-content {
                padding: 10px 15px;
                border-radius: 8px;
                font-size: 14px;
                line-height: 1.5;
                max-width: 85%;
            }
            
            .user-content {
                background: #3b82f6;
                color: white;
                margin-left: auto;
                border-radius: 8px 8px 0 8px;
            }
            
            .agent-content {
                background: white;
                border: 1px solid #e5e7eb;
                margin-right: auto;
            }
            
            .system-content {
                background: #f3f4f6;
                color: #6b7280;
                text-align: center;
                font-size: 12px;
                margin: 10px auto;
                max-width: 70%;
            }
            
            .error-content {
                background: #fee2e2;
                color: #dc2626;
                text-align: center;
                margin: 10px auto;
                max-width: 70%;
            }
            
            .group-chat-input-area {
                background: white;
                border-top: 1px solid #e5e7eb;
                padding: 15px;
                border-radius: 0 0 12px 12px;
            }
            
            .working-directory-indicator {
                display: flex;
                align-items: center;
                gap: 5px;
                font-size: 11px;
                color: #6b7280;
                margin-bottom: 10px;
            }
            
            .group-chat-input-wrapper {
                display: flex;
                gap: 10px;
            }
            
            .group-chat-input {
                flex: 1;
                padding: 10px 15px;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                font-size: 14px;
                transition: all 0.2s;
            }
            
            .group-chat-input:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }
            
            .group-chat-send {
                background: #667eea;
                color: white;
                border: none;
                width: 40px;
                height: 40px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .group-chat-send:hover {
                background: #5a67d8;
                transform: scale(1.05);
            }
        `;
        
        document.head.appendChild(styles);
    }
}

// Export a function to start a group chat
export function startGroupChat(agents, initialMessage, workingDirectory) {
    return new GroupChat(agents, initialMessage, workingDirectory);
}