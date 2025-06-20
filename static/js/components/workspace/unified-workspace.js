// Unified Workspace Component - The new command center for multi-agent collaboration
import { createElement, updateIcons, showNotification } from '../../utils/dom-helpers.js';
import { getAgentById, getAgentColor, AGENTS } from '../../agents/agent-config.js';
import { formatAgentResponse } from '../../utils/formatters.js';
import { ProcessFlow } from './process-flow.js';
import { AgentDock } from './agent-dock.js';

export class UnifiedWorkspace {
    constructor(agentManager, wsService, apiClient) {
        this.agentManager = agentManager;
        this.wsService = wsService;
        this.apiClient = apiClient;
        this.activeAgents = new Set();
        this.currentTaskId = null;
        this.container = null;
        this.processFlow = new ProcessFlow();
        this.agentDock = new AgentDock();
        this.messages = [];
        this.isCollaborationMode = false;
    }

    init() {
        this.render();
        this.setupEventListeners();
        this.agentDock.init(this.handleAgentSelection.bind(this));
        this.processFlow.init();
    }

    render() {
        // Replace the entire main content area with our workspace
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;

        mainContent.innerHTML = '';
        
        this.container = createElement('div', 'unified-workspace');
        this.container.innerHTML = `
            <div class="workspace-layout">
                <!-- Agent Dock - Left Panel -->
                <aside class="agent-dock-panel" id="agent-dock-container">
                    <!-- Agent dock will be rendered here -->
                </aside>

                <!-- Command Center - Main Area -->
                <main class="command-center">
                    <header class="workspace-header">
                        <div class="header-content">
                            <h1 class="workspace-title">
                                <span id="workspace-mode">Agent Command Center</span>
                            </h1>
                            <p class="workspace-subtitle" id="workspace-subtitle">
                                Select agents to start a conversation or collaboration
                            </p>
                        </div>
                        <div class="header-actions">
                            <button class="btn btn-secondary" id="clear-workspace">
                                <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                                Clear
                            </button>
                            <button class="btn btn-primary" id="start-collaboration">
                                <i data-lucide="play" class="w-4 h-4"></i>
                                Start Task
                            </button>
                        </div>
                    </header>

                    <!-- Conversation Area -->
                    <div class="conversation-area" id="conversation-area">
                        <div class="empty-state" id="empty-state">
                            <i data-lucide="messages-square" class="w-16 h-16 text-gray-300"></i>
                            <h3>Start a Conversation</h3>
                            <p>Select agents from the dock or type a message to begin</p>
                        </div>
                    </div>

                    <!-- Command Input -->
                    <div class="command-input-area">
                        <div class="active-agents-bar" id="active-agents-bar">
                            <!-- Active agent chips will appear here -->
                        </div>
                        <div class="command-input-wrapper">
                            <textarea 
                                id="command-input" 
                                class="command-input" 
                                placeholder="Type your message or @ to mention an agent..."
                                rows="1"
                            ></textarea>
                            <div class="input-actions">
                                <label class="enhance-toggle">
                                    <input type="checkbox" id="enhance-prompt" checked>
                                    <span>Enhance</span>
                                </label>
                                <button class="send-button" id="send-command">
                                    <i data-lucide="send" class="w-4 h-4"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </main>

                <!-- Process View - Right Panel -->
                <aside class="process-panel" id="process-panel">
                    <div class="panel-header">
                        <h3>Process Flow</h3>
                        <button class="panel-toggle" id="toggle-process-panel">
                            <i data-lucide="x" class="w-4 h-4"></i>
                        </button>
                    </div>
                    <div id="process-flow-container">
                        <!-- Process flow visualization will be rendered here -->
                    </div>
                    <div class="timeline-section">
                        <h4>Activity Timeline</h4>
                        <div id="activity-timeline" class="activity-timeline">
                            <!-- Timeline events will appear here -->
                        </div>
                    </div>
                </aside>
            </div>
        `;

        mainContent.appendChild(this.container);
        
        // Render sub-components
        const agentDockContainer = document.getElementById('agent-dock-container');
        agentDockContainer.appendChild(this.agentDock.render());
        
        const processFlowContainer = document.getElementById('process-flow-container');
        processFlowContainer.appendChild(this.processFlow.render());
        
        updateIcons();
    }

    setupEventListeners() {
        // Command input
        const commandInput = document.getElementById('command-input');
        const sendButton = document.getElementById('send-command');
        
        commandInput.addEventListener('input', (e) => this.handleInputChange(e));
        commandInput.addEventListener('keydown', (e) => this.handleKeyDown(e));
        sendButton.addEventListener('click', () => this.sendMessage());
        
        // Clear workspace
        document.getElementById('clear-workspace').addEventListener('click', () => this.clearWorkspace());
        
        // Start collaboration
        document.getElementById('start-collaboration').addEventListener('click', () => this.startCollaborationMode());
        
        // Panel toggle
        document.getElementById('toggle-process-panel').addEventListener('click', () => this.toggleProcessPanel());
        
        // WebSocket listeners
        if (this.wsService) {
            this.wsService.on('agent_response', (data) => this.handleAgentResponse(data));
            this.wsService.on('agent_communication', (data) => this.handleAgentCommunication(data));
            this.wsService.on('task_progress', (data) => this.handleTaskProgress(data));
        }
        
        // Listen for @ mentions
        this.setupMentionListener();
    }

    handleAgentSelection(agentId, selected) {
        if (selected) {
            this.activeAgents.add(agentId);
        } else {
            this.activeAgents.delete(agentId);
        }
        
        this.updateActiveAgentsBar();
        this.updateWorkspaceHeader();
        
        // Update process flow
        this.processFlow.updateActiveAgents(Array.from(this.activeAgents));
    }

    updateActiveAgentsBar() {
        const bar = document.getElementById('active-agents-bar');
        bar.innerHTML = '';
        
        if (this.activeAgents.size === 0) {
            bar.style.display = 'none';
            return;
        }
        
        bar.style.display = 'flex';
        
        this.activeAgents.forEach(agentId => {
            const agent = getAgentById(agentId);
            if (!agent) return;
            
            const chip = createElement('div', 'agent-chip');
            const colorClass = getAgentColor(agent.color);
            
            chip.innerHTML = `
                <div class="chip-avatar ${colorClass}">
                    <i data-lucide="${agent.icon}" class="w-3 h-3 text-white"></i>
                </div>
                <span class="chip-name">${agent.name}</span>
                <button class="chip-remove" data-agent="${agentId}">
                    <i data-lucide="x" class="w-3 h-3"></i>
                </button>
            `;
            
            chip.querySelector('.chip-remove').addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeAgent(agentId);
            });
            
            bar.appendChild(chip);
        });
        
        updateIcons();
    }

    updateWorkspaceHeader() {
        const title = document.getElementById('workspace-mode');
        const subtitle = document.getElementById('workspace-subtitle');
        
        if (this.activeAgents.size === 0) {
            title.textContent = 'Agent Command Center';
            subtitle.textContent = 'Select agents to start a conversation or collaboration';
        } else if (this.activeAgents.size === 1) {
            const agent = getAgentById(Array.from(this.activeAgents)[0]);
            title.textContent = `Conversation with ${agent.name}`;
            subtitle.textContent = agent.role;
        } else {
            title.textContent = 'Multi-Agent Collaboration';
            const agentNames = Array.from(this.activeAgents)
                .map(id => getAgentById(id)?.name)
                .filter(Boolean)
                .join(', ');
            subtitle.textContent = `Collaborating with: ${agentNames}`;
        }
    }

    removeAgent(agentId) {
        this.activeAgents.delete(agentId);
        this.agentDock.setAgentActive(agentId, false);
        this.updateActiveAgentsBar();
        this.updateWorkspaceHeader();
        this.processFlow.updateActiveAgents(Array.from(this.activeAgents));
    }

    async sendMessage() {
        const input = document.getElementById('command-input');
        const message = input.value.trim();
        
        if (!message || this.activeAgents.size === 0) {
            showNotification('Please select at least one agent and enter a message', 'warning');
            return;
        }
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        
        // Hide empty state
        document.getElementById('empty-state').style.display = 'none';
        
        // Add user message to conversation
        this.addMessage('user', message, 'You');
        
        // Handle different modes
        if (this.isCollaborationMode && this.activeAgents.size > 1) {
            await this.sendCollaborationMessage(message);
        } else {
            await this.sendDirectMessage(message);
        }
    }

    async sendDirectMessage(message) {
        const agentId = Array.from(this.activeAgents)[0];
        const enhancePrompt = document.getElementById('enhance-prompt').checked;
        
        try {
            // Update agent status
            this.agentDock.updateAgentStatus(agentId, 'working');
            this.processFlow.setAgentStatus(agentId, 'working');
            
            // Send via API
            const response = await this.apiClient.sendMessage(agentId, message, enhancePrompt);
            
            if (response.success) {
                // Response will come through WebSocket
                this.addTimelineEvent(`Message sent to ${getAgentById(agentId).name}`);
            }
        } catch (error) {
            console.error('Error sending message:', error);
            showNotification('Failed to send message', 'error');
            this.agentDock.updateAgentStatus(agentId, 'ready');
        }
    }

    async sendCollaborationMessage(message) {
        const agentIds = Array.from(this.activeAgents);
        const enhancePrompt = document.getElementById('enhance-prompt').checked;
        
        try {
            // Create collaboration task
            const response = await this.apiClient.startCollaboration(
                message,
                agentIds,
                '/Users/copp1723/Desktop',
                false,
                enhancePrompt
            );
            
            if (response.success) {
                this.currentTaskId = response.task_id;
                
                // Update all agents to working
                agentIds.forEach(id => {
                    this.agentDock.updateAgentStatus(id, 'working');
                    this.processFlow.setAgentStatus(id, 'working');
                });
                
                // Join WebSocket room
                if (this.wsService) {
                    this.wsService.joinTask(response.task_id);
                }
                
                this.addTimelineEvent('Collaboration task started');
                showNotification('Agents are collaborating on your request', 'success');
            }
        } catch (error) {
            console.error('Error starting collaboration:', error);
            showNotification('Failed to start collaboration', 'error');
        }
    }

    addMessage(type, content, sender, agentId = null) {
        const conversationArea = document.getElementById('conversation-area');
        const messageGroup = createElement('div', 'message-group fade-in');
        
        if (type === 'user') {
            messageGroup.innerHTML = `
                <div class="user-message">
                    <div class="message-content">
                        <div class="message-text">${content}</div>
                    </div>
                </div>
            `;
        } else if (type === 'agent') {
            const agent = agentId ? getAgentById(agentId) : null;
            const colorClass = agent ? getAgentColor(agent.color) : 'bg-gray-500';
            const icon = agent ? agent.icon : 'message-circle';
            
            messageGroup.innerHTML = `
                <div class="agent-message">
                    <div class="message-avatar ${colorClass}">
                        <i data-lucide="${icon}" class="w-4 h-4 text-white"></i>
                    </div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-sender">${sender}</span>
                            <span class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                        </div>
                        <div class="message-text">${formatAgentResponse(content)}</div>
                    </div>
                </div>
            `;
        } else if (type === 'communication') {
            messageGroup.innerHTML = `
                <div class="agent-communication-inline">
                    <i data-lucide="git-merge" class="w-4 h-4"></i>
                    <span>${content}</span>
                </div>
            `;
        }
        
        conversationArea.appendChild(messageGroup);
        updateIcons();
        
        // Scroll to bottom
        conversationArea.scrollTop = conversationArea.scrollHeight;
        
        // Store message
        this.messages.push({ type, content, sender, agentId, timestamp: new Date() });
    }

    handleAgentResponse(data) {
        const agentId = data.agent_id;
        const agent = getAgentById(agentId);
        
        if (agent && this.activeAgents.has(agentId)) {
            this.addMessage('agent', data.content, agent.name, agentId);
            this.agentDock.updateAgentStatus(agentId, 'ready');
            this.processFlow.setAgentStatus(agentId, 'completed');
            this.addTimelineEvent(`${agent.name} responded`);
        }
    }

    handleAgentCommunication(data) {
        const comm = data.communication || data;
        const fromAgent = getAgentById(comm.from_agent);
        const toAgent = getAgentById(comm.to_agent);
        
        if (fromAgent && toAgent) {
            this.addMessage(
                'communication',
                `${fromAgent.name} is consulting with ${toAgent.name}`
            );
            
            // Update process flow
            this.processFlow.showCommunication(comm.from_agent, comm.to_agent);
        }
    }

    handleTaskProgress(data) {
        if (data.task_id === this.currentTaskId && data.progress) {
            this.processFlow.updateProgress(data.progress);
            
            // Update agent statuses
            if (data.agent_statuses) {
                Object.entries(data.agent_statuses).forEach(([agentId, status]) => {
                    this.agentDock.updateAgentStatus(agentId, status.status);
                    this.processFlow.setAgentStatus(agentId, status.status);
                });
            }
        }
    }

    addTimelineEvent(event) {
        const timeline = document.getElementById('activity-timeline');
        const eventEl = createElement('div', 'timeline-event');
        
        eventEl.innerHTML = `
            <div class="event-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
            <div class="event-text">${event}</div>
        `;
        
        timeline.appendChild(eventEl);
        timeline.scrollTop = timeline.scrollHeight;
        
        // Keep only last 10 events
        while (timeline.children.length > 10) {
            timeline.removeChild(timeline.firstChild);
        }
    }

    startCollaborationMode() {
        if (this.activeAgents.size < 2) {
            showNotification('Please select at least 2 agents for collaboration', 'warning');
            return;
        }
        
        this.isCollaborationMode = true;
        document.getElementById('start-collaboration').innerHTML = `
            <i data-lucide="stop-circle" class="w-4 h-4"></i>
            End Task
        `;
        
        const input = document.getElementById('command-input');
        input.placeholder = 'Describe the task for the agents to collaborate on...';
        input.focus();
        
        updateIcons();
        showNotification('Collaboration mode active. Describe your task.', 'info');
    }

    clearWorkspace() {
        this.activeAgents.clear();
        this.messages = [];
        this.currentTaskId = null;
        this.isCollaborationMode = false;
        
        // Reset UI
        document.getElementById('conversation-area').innerHTML = `
            <div class="empty-state" id="empty-state">
                <i data-lucide="messages-square" class="w-16 h-16 text-gray-300"></i>
                <h3>Start a Conversation</h3>
                <p>Select agents from the dock or type a message to begin</p>
            </div>
        `;
        
        document.getElementById('activity-timeline').innerHTML = '';
        document.getElementById('start-collaboration').innerHTML = `
            <i data-lucide="play" class="w-4 h-4"></i>
            Start Task
        `;
        
        this.agentDock.clearSelections();
        this.processFlow.reset();
        this.updateActiveAgentsBar();
        this.updateWorkspaceHeader();
        
        updateIcons();
        showNotification('Workspace cleared', 'success');
    }

    toggleProcessPanel() {
        const panel = document.getElementById('process-panel');
        panel.classList.toggle('collapsed');
        
        const icon = document.querySelector('#toggle-process-panel i');
        if (panel.classList.contains('collapsed')) {
            icon.setAttribute('data-lucide', 'chevron-left');
        } else {
            icon.setAttribute('data-lucide', 'x');
        }
        updateIcons();
    }

    setupMentionListener() {
        const input = document.getElementById('command-input');
        
        input.addEventListener('input', (e) => {
            const value = e.target.value;
            const lastChar = value[value.length - 1];
            
            if (lastChar === '@') {
                this.showAgentMentionDropdown(e.target);
            }
        });
    }

    showAgentMentionDropdown(input) {
        // This would show a dropdown of available agents
        // For now, we'll just show a notification
        showNotification('Type agent name or select from dock', 'info');
    }

    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    handleInputChange(e) {
        // Auto-resize textarea
        e.target.style.height = 'auto';
        e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
    }
}
