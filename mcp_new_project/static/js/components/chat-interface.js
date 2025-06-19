// Chat Interface Component
import { AgentAPI } from '../services/api.js';
import { StorageService } from '../services/storage.js';
import { DirectoryBrowser } from './directory-browser.js';
import { createElement, escapeHtml, showNotification, updateIcons } from '../utils/dom-helpers.js';
import { formatAgentResponse } from '../utils/formatters.js';
import { getAgentById, getAgentColor, AGENTS } from '../agents/agent-config.js';
import { startGroupChat } from './group-chat.js';

export class ChatInterface {
    constructor(agentId) {
        this.agentId = agentId;
        this.agent = getAgentById(agentId);
        this.api = new AgentAPI();
        this.storage = new StorageService();
        this.directoryBrowser = new DirectoryBrowser();
        this.container = null;
        this.chatArea = null;
        this.input = null;
        this.modelSelector = null;
        this.isActive = false;
        this.workingDirectory = this.storage.getAgentDirectory(agentId);
    }

    render() {
        this.container = createElement('div', 'agent-chat-container');
        this.container.id = `chat-container-${this.agentId}`;
        
        this.container.innerHTML = `
            <div class="bg-white rounded-xl shadow-sm border border-gray-200">
                <!-- Agent Header -->
                <div class="p-6 border-b border-gray-100">
                    <div class="flex items-start justify-between">
                        <div class="flex-1">
                            <div class="flex items-center space-x-3">
                                <div class="status-indicator w-3 h-3 rounded-full bg-gray-400"></div>
                                <h2 class="text-xl font-semibold text-gray-900">${this.agent.name}</h2>
                                <span class="px-3 py-1 text-xs font-medium bg-${this.agent.color}-100 text-${this.agent.color}-700 rounded-full">
                                    ${this.agent.id.split('_')[0].toUpperCase()}
                                </span>
                            </div>
                            <p class="text-sm text-gray-600 mt-1">${this.agent.role}</p>
                        </div>
                        
                        <div class="flex items-center space-x-2">
                            <!-- Action Buttons -->
                            <button id="copy-${this.agentId}" title="Copy chat contents" class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                                <i data-lucide="copy" class="w-4 h-4"></i>
                            </button>
                            <button id="clear-${this.agentId}" title="Clear chat history" class="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                            </button>
                            
                            <!-- Model Selector -->
                            <select id="model-${this.agentId}" class="model-selector px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                                <option value="openai/gpt-4.1" title="GPT 4.1: Latest all-around model">GPT 4.1</option>
                                <option value="openai/o3-pro" title="O3 Pro: Advanced general reasoning">O3 Pro</option>
                                <option value="openai/codex-mini" title="Codex Mini: Quick and efficient">Codex Mini</option>
                                <option value="anthropic/claude-4-opus" title="Claude 4 Opus: Excellent reasoning">Claude 4 Opus</option>
                                <option value="anthropic/claude-4-sonnet" title="Claude 4 Sonnet: Fast and capable">Claude 4 Sonnet</option>
                                <option value="deepseek/deepseek-v3" title="DeepSeek V3: Versatile model">DeepSeek V3</option>
                                <option value="deepseek/deepseek-r1" title="DeepSeek R1: General reasoning">DeepSeek R1</option>
                                <option value="google/gemini-2.5-pro" title="Gemini 2.5 Pro: Google's best">Gemini 2.5 Pro</option>
                                <option value="x-ai/grok-3" title="Grok 3: X.AI's flagship">Grok 3</option>
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- Chat Area -->
                <div class="chat-area overflow-y-auto p-6 bg-gray-50" id="chat-${this.agentId}">
                    <div class="text-center text-gray-500 text-sm">
                        <i data-lucide="message-square" class="w-12 h-12 text-gray-300 mx-auto mb-3"></i>
                        <p>No messages yet. Start a conversation with ${this.agent.name}!</p>
                    </div>
                </div>
                
                <!-- Input Area -->
                <div class="p-6 border-t border-gray-100">
                    <div class="flex items-center space-x-2">
                        <!-- Directory selector button -->
                        <button id="dir-${this.agentId}" title="Select working directory" class="p-3 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                            <i data-lucide="folder" class="w-5 h-5"></i>
                        </button>
                        
                        <!-- File upload button -->
                        <input type="file" id="upload-${this.agentId}" class="hidden">
                        <button id="upload-btn-${this.agentId}" title="Attach file" class="p-3 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
                            <i data-lucide="paperclip" class="w-5 h-5"></i>
                        </button>
                        
                        <!-- Message input -->
                        <input type="text" 
                               class="chat-input flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                               id="input-${this.agentId}" 
                               placeholder="Type your message to ${this.agent.name}...">
                        
                        <!-- Send button -->
                        <button id="send-${this.agentId}" class="p-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                            <i data-lucide="send" class="w-5 h-5"></i>
                        </button>
                    </div>
                    
                    <!-- Status indicators -->
                    <div class="flex items-center justify-between mt-2 text-xs text-gray-500">
                        <span class="directory-label" id="directory-label-${this.agentId}">
                            ${this.workingDirectory ? this.workingDirectory : 'No directory selected'}
                        </span>
                        <span class="file-label" id="file-label-${this.agentId}"></span>
                    </div>
                </div>
            </div>
        `;

        // Defer initialization until after DOM insertion
        setTimeout(() => {
            this.setupElements();
            this.attachEventListeners();
            this.loadChatHistory();
            this.loadPreferences();
        }, 0);
        
        return this.container;
    }

    setupElements() {
        this.chatArea = document.getElementById(`chat-${this.agentId}`);
        this.input = document.getElementById(`input-${this.agentId}`);
        this.modelSelector = document.getElementById(`model-${this.agentId}`);
    }

    attachEventListeners() {
        // Send message
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });
        document.getElementById(`send-${this.agentId}`).addEventListener('click', () => this.sendMessage());
        
        // Directory browser
        document.getElementById(`dir-${this.agentId}`).addEventListener('click', () => this.selectDirectory());
        
        // File upload
        const uploadInput = document.getElementById(`upload-${this.agentId}`);
        const uploadBtn = document.getElementById(`upload-btn-${this.agentId}`);
        uploadBtn.addEventListener('click', () => uploadInput.click());
        uploadInput.addEventListener('change', () => this.uploadFile());
        
        // Copy and clear
        document.getElementById(`copy-${this.agentId}`).addEventListener('click', () => this.copyChat());
        document.getElementById(`clear-${this.agentId}`).addEventListener('click', () => this.clearChat());
        
        // Model selector
        this.modelSelector.addEventListener('change', () => {
            this.storage.setModelPreference(this.agentId, this.modelSelector.value);
        });
    }

    async sendMessage() {
        let message = this.input.value.trim();
        if (!message) return;
        
        // Check for @mentions - handle both @agentname and @agent name patterns
        const mentionPattern = /@(\w+(?:\s+\w+)?)/g;
        const mentions = [...message.matchAll(mentionPattern)].map(match => {
            // Remove spaces and convert to lowercase for matching
            return match[1].replace(/\s+/g, '').toLowerCase();
        });
        
        if (mentions.length > 0) {
            // Add the user's message to the chat first
            this.addMessage(message, 'user');
            
            // Find mentioned agents
            const mentionedAgents = [];
            for (const mention of mentions) {
                const agent = AGENTS.find(a => 
                    a.id.toLowerCase().includes(mention) || 
                    a.name.toLowerCase().includes(mention) ||
                    a.id.toLowerCase().replace('_', '') === mention ||
                    a.name.toLowerCase().replace(/\s+/g, '') === mention
                );
                if (agent && agent.id !== this.agentId) {
                    mentionedAgents.push(agent);
                }
            }
            
            if (mentionedAgents.length > 0) {
                // Start group chat with mentioned agents
                const currentAgent = getAgentById(this.agentId);
                const groupChat = startGroupChat([currentAgent, ...mentionedAgents], message, this.workingDirectory);
                
                // The group chat will handle sending the initial message
                // Just clear the input here
                this.input.value = '';
                
                // Add notification in current chat
                this.addMessage(
                    `Started group chat with ${mentionedAgents.map(a => '@' + a.name).join(', ')}`, 
                    'assistant',
                    '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-800 ml-2">Group Chat</span>'
                );
            } else {
                showNotification('No valid agents mentioned', 'warning');
            }
            
            this.input.value = '';
            return;
        }
        
        // Add directory context if selected
        if (this.workingDirectory && !message.includes('[Working in:')) {
            message = `[Working in: ${this.workingDirectory}]\n${message}`;
        }
        
        const model = this.modelSelector.value;
        this.input.value = '';
        
        // Add user message
        this.addMessage(message, 'user');
        
        // Update status
        this.updateStatus(true);
        
        // Add typing indicator
        const typingId = this.addTypingIndicator();
        
        try {
            const enhancePrompt = this.storage.getEnhancePromptSetting();
            const data = await this.api.sendMessage(this.agentId, message, model, enhancePrompt);
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            if (data.success) {
                const enhancedBadge = data.enhanced ? 
                    '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 ml-2">Enhanced</span>' : '';
                this.addMessage(data.response, 'assistant', enhancedBadge);
            } else {
                this.addMessage(data.error, 'error');
            }
        } catch (err) {
            this.removeTypingIndicator(typingId);
            this.addMessage('Failed to send message', 'error');
        } finally {
            this.updateStatus(false);
        }
    }

    addMessage(content, role, badge = '') {
        const msgDiv = createElement('div', 'chat-message animate-slide-in');
        
        if (role === 'user') {
            msgDiv.classList.add('flex', 'justify-end');
            msgDiv.innerHTML = `
                <div class="max-w-[80%] px-4 py-2 bg-blue-600 text-white rounded-lg rounded-br-none text-sm">
                    ${escapeHtml(content)}
                </div>
            `;
        } else if (role === 'assistant') {
            msgDiv.innerHTML = `
                <div class="max-w-[80%]">
                    <div class="flex items-center space-x-2 mb-2">
                        <div class="font-medium text-xs text-gray-600">${this.agent.name}</div>
                        ${badge}
                    </div>
                    <div class="px-6 py-4 bg-gray-100 text-gray-800 rounded-lg rounded-bl-none shadow-sm">
                        <div class="agent-response text-sm leading-relaxed">${formatAgentResponse(content)}</div>
                    </div>
                </div>
            `;
        } else if (role === 'error') {
            msgDiv.innerHTML = `
                <div class="max-w-[80%] px-4 py-2 bg-red-50 text-red-800 rounded-lg rounded-bl-none text-sm">
                    <div class="font-medium text-xs text-red-600 mb-1">Error</div>
                    ${escapeHtml(content)}
                </div>
            `;
        }
        
        this.chatArea.appendChild(msgDiv);
        this.chatArea.scrollTop = this.chatArea.scrollHeight;
        updateIcons();
    }

    addTypingIndicator() {
        const typingId = `typing-${this.agentId}-${Date.now()}`;
        const typingDiv = createElement('div', 'chat-message animate-slide-in flex items-center space-x-2');
        typingDiv.id = typingId;
        typingDiv.innerHTML = `
            <div class="flex space-x-1 px-4 py-2 bg-gray-100 rounded-lg">
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></div>
            </div>
        `;
        this.chatArea.appendChild(typingDiv);
        this.chatArea.scrollTop = this.chatArea.scrollHeight;
        return typingId;
    }

    removeTypingIndicator(typingId) {
        const typing = document.getElementById(typingId);
        if (typing) typing.remove();
    }

    updateStatus(isActive) {
        const indicator = this.container.querySelector('.status-indicator');
        if (indicator) {
            if (isActive) {
                indicator.classList.remove('bg-gray-400');
                indicator.classList.add('bg-green-500');
            } else {
                indicator.classList.remove('bg-green-500');
                indicator.classList.add('bg-gray-400');
            }
        }
    }

    async selectDirectory() {
        const selectedPath = await this.directoryBrowser.open(this.workingDirectory);
        if (selectedPath) {
            this.workingDirectory = selectedPath;
            this.storage.setAgentDirectory(this.agentId, selectedPath);
            document.getElementById(`directory-label-${this.agentId}`).textContent = selectedPath;
            showNotification(`Directory selected for ${this.agent.name}: ${selectedPath}`, 'success');
        }
    }

    async uploadFile() {
        const fileInput = document.getElementById(`upload-${this.agentId}`);
        const fileLabel = document.getElementById(`file-label-${this.agentId}`);
        
        if (fileInput.files.length === 0) {
            showNotification('Please select a file to upload.', 'warning');
            return;
        }

        const file = fileInput.files[0];
        fileLabel.textContent = file.name;

        this.addMessage(`Uploading: ${file.name}`, 'user');
        this.updateStatus(true);

        try {
            const data = await this.api.uploadFile(this.agentId, file);
            
            if (data.success) {
                this.addMessage(data.agent_response, 'assistant');
            } else {
                this.addMessage(data.error, 'error');
            }
        } catch (err) {
            this.addMessage('Failed to upload file', 'error');
        } finally {
            this.updateStatus(false);
            fileInput.value = '';
            fileLabel.textContent = '';
        }
    }

    async loadChatHistory() {
        try {
            const data = await this.api.getChatHistory(this.agentId);
            
            if (data.success && data.history && data.history.length > 0) {
                this.chatArea.innerHTML = ''; // Clear empty state
                
                data.history.forEach(msg => {
                    if (msg.role === 'user') {
                        this.addMessage(msg.content, 'user');
                    } else if (msg.role === 'assistant') {
                        this.addMessage(msg.content, 'assistant');
                    }
                });
            }
        } catch (err) {
            console.error(`Error loading chat history for ${this.agentId}:`, err);
        }
    }

    loadPreferences() {
        const savedModel = this.storage.getModelPreference(this.agentId);
        if (savedModel) {
            this.modelSelector.value = savedModel;
        }
    }

    async clearChat() {
        if (!confirm(`Are you sure you want to clear the chat history for ${this.agent.name}?`)) {
            return;
        }
        
        try {
            const success = await this.api.clearChatHistory(this.agentId);
            
            if (success) {
                this.chatArea.innerHTML = `
                    <div class="text-center text-gray-500 text-sm">
                        <i data-lucide="message-square" class="w-12 h-12 text-gray-300 mx-auto mb-3"></i>
                        <p>No messages yet. Start a conversation with ${this.agent.name}!</p>
                    </div>
                `;
                updateIcons();
                showNotification('Chat history cleared successfully', 'success');
            } else {
                showNotification('Failed to clear chat history', 'error');
            }
        } catch (error) {
            console.error('Error clearing chat:', error);
            showNotification('Failed to clear chat history', 'error');
        }
    }

    copyChat() {
        const messages = this.chatArea.querySelectorAll('.chat-message');
        let chatText = `Chat History - ${this.agent.name}\n${'='.repeat(40)}\n\n`;
        
        messages.forEach(msg => {
            const isUser = msg.classList.contains('justify-end');
            const role = isUser ? 'User' : this.agent.name;
            const content = msg.querySelector('div > div').textContent.trim();
            chatText += `${role}: ${content}\n\n`;
        });
        
        navigator.clipboard.writeText(chatText).then(() => {
            showNotification('Chat history copied to clipboard', 'success');
        }).catch(err => {
            console.error('Error copying to clipboard:', err);
            showNotification('Failed to copy chat history', 'error');
        });
    }

    show() {
        this.container.classList.add('active');
        this.isActive = true;
        setTimeout(() => this.input.focus(), 100);
    }

    hide() {
        this.container.classList.remove('active');
        this.isActive = false;
    }
}