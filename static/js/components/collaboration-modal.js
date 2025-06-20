// Collaboration Modal Component
import { AGENTS, getAgentById, getAgentByName, getAgentColor } from '../agents/agent-config.js';
import { AgentAPI } from '../services/api.js';
import { DirectoryBrowser } from './directory-browser.js';
import { createElement, escapeHtml, showNotification, updateIcons } from '../utils/dom-helpers.js';
import { formatAgentResponse } from '../utils/formatters.js';
import { startGroupChat } from './group-chat.js';

export class CollaborationModal {
    constructor(agentManager, websocketService) {
        this.agentManager = agentManager;
        this.wsService = websocketService;
        this.api = new AgentAPI();
        this.directoryBrowser = new DirectoryBrowser();
        this.modal = null;
        this.activeTaskId = null;
        this.templates = [];
    }

    async init() {
        await this.loadWorkflowTemplates();
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Open modal button
        const openBtn = document.getElementById('open-collab-btn');
        if (openBtn) {
            openBtn.addEventListener('click', () => this.open());
        }
        
        // Listen for agent mention events from chat interfaces
        document.addEventListener('agent-mention', (event) => {
            this.handleAgentMention(event.detail);
        });
        
        // WebSocket listeners
        if (this.wsService) {
            this.wsService.on('agent_communication', (data) => {
                if (data.task_id === this.activeTaskId) {
                    this.handleAgentCommunication(data);
                }
            });
            
            this.wsService.on('task_progress', (data) => {
                if (data.task_id === this.activeTaskId) {
                    this.updateProgress(data);
                }
            });
        }
    }

    open() {
        // Grab (or create) the modal element
        this.modal = document.getElementById('collab-modal');

        // Re-create if it doesn’t exist *or* was injected but left empty
        if (!this.modal || this.modal.children.length === 0) {
            /* eslint-disable no-console */
            console.log('CollaborationModal: creating modal markup…');
            /* eslint-enable no-console */
            this.createModal();
        }

        if (this.modal) {
            this.modal.classList.remove('hidden');
            // Give the browser a moment to paint new DOM before we query for inner elements
            setTimeout(() => {
                this.populateAgentCheckboxes();
                this.populateTemplates();
            }, 10);
        } else {
            // This should never happen, but log in case
            /* eslint-disable no-console */
            console.error('CollaborationModal: failed to create or locate collab-modal container');
            /* eslint-enable no-console */
        }
    }

    close() {
        if (this.modal) {
            this.modal.classList.add('hidden');
        }
        this.activeTaskId = null;
    }

    createModal() {
        this.modal = createElement('div', 'hidden fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50');
        this.modal.id = 'collab-modal';
        
        this.modal.innerHTML = `
            <div class="bg-white rounded-xl shadow-2xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto">
                <div class="p-6 border-b border-gray-200">
                    <div class="flex items-center justify-between">
                        <h2 class="text-2xl font-bold text-gray-900">Multi-Agent Collaboration</h2>
                        <button id="close-collab-modal" class="text-gray-400 hover:text-gray-600">
                            <i data-lucide="x" class="w-6 h-6"></i>
                        </button>
                    </div>
                </div>
                
                <div class="p-6">
                    <!-- Workflow Template Selection -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Workflow Template (Optional)</label>
                        <select id="workflow-template" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            <option value="">Select a workflow template...</option>
                        </select>
                    </div>
                    
                    <!-- Task Description -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Task Description</label>
                        <textarea id="collab-task" rows="3" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" placeholder="Describe the task you want the agents to collaborate on..."></textarea>
                    </div>
                    
                    <!-- Agent Selection -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Select Agents</label>
                        <p class="text-xs text-gray-500 mb-2">Note: General Assistant is always included for executive summary</p>
                        <div class="grid grid-cols-2 gap-3" id="agent-checkboxes">
                            <!-- Checkboxes will be populated here -->
                        </div>
                    </div>
                    
                    <!-- Working Directory -->
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Working Directory</label>
                        <div class="flex items-center space-x-2">
                            <button id="select-collab-dir" class="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors border border-gray-300">
                                <i data-lucide="folder" class="w-5 h-5"></i>
                            </button>
                            <input type="text" 
                                   id="collab-working-dir" 
                                   class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm" 
                                   placeholder="Select or enter working directory..." 
                                   value="/Users/copp1723/Desktop">
                        </div>
                    </div>
                    
                    <!-- Submit Button -->
                    <div class="flex items-center justify-between">
                        <label class="flex items-center">
                            <input type="checkbox" id="enhance-prompt-collab" class="mr-2" checked>
                            <span class="text-sm text-gray-700">Enhance prompt</span>
                        </label>
                        <button id="start-collab" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                            Start Collaboration
                        </button>
                    </div>
                    
                    <!-- Results Area -->
                    <div id="collab-results" class="mt-6 hidden">
                        <!-- Enhanced progress tracking will be populated here -->
                    </div>
                    
                    <!-- Advanced Progress Tracking Dashboard -->
                    <div id="progress-dashboard" class="mt-6 hidden">
                        <div class="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-6 border border-blue-200">
                            <div class="flex items-center justify-between mb-4">
                                <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                                    <i data-lucide="activity" class="w-5 h-5 mr-2 text-blue-600"></i>
                                    Collaboration Progress
                                </h3>
                                <span id="task-status" class="px-3 py-1 text-sm font-medium rounded-full bg-blue-100 text-blue-700">Initializing...</span>
                            </div>
                            
                            <!-- Overall Progress Bar -->
                            <div class="mb-6">
                                <div class="flex items-center justify-between text-sm mb-2">
                                    <span class="text-gray-600">Overall Progress</span>
                                    <span id="overall-progress-text" class="font-medium text-gray-900">0%</span>
                                </div>
                                <div class="w-full bg-gray-200 rounded-full h-3 shadow-inner">
                                    <div id="overall-progress-bar" class="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-500 ease-out shadow-sm" style="width: 0%"></div>
                                </div>
                            </div>
                            
                            <!-- Agent Status Grid -->
                            <div id="agent-status-grid" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                                <!-- Agent status cards will be populated here -->
                            </div>
                            
                            <!-- Timeline -->
                            <div class="border-t border-gray-200 pt-4">
                                <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center">
                                    <i data-lucide="clock" class="w-4 h-4 mr-2"></i>
                                    Activity Timeline
                                </h4>
                                <div id="activity-timeline" class="space-y-2 max-h-32 overflow-y-auto">
                                    <!-- Timeline events will be populated here -->
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Collaboration Chat Window -->
                    <div id="collab-chat-window" class="mt-6 hidden">
                        <div class="border-t pt-4">
                            <h3 class="text-lg font-semibold mb-3 flex items-center">
                                <i data-lucide="messages-square" class="w-5 h-5 mr-2"></i>
                                Collaboration Progress
                            </h3>
                            <div id="collab-chat-area" class="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto space-y-3">
                                <!-- Agent responses will appear here -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.modal);
        
        // Attach event listeners
        document.getElementById('close-collab-modal').addEventListener('click', () => this.close());
        document.getElementById('select-collab-dir').addEventListener('click', () => this.selectDirectory());
        document.getElementById('start-collab').addEventListener('click', () => this.startCollaboration());
        
        const templateSelect = document.getElementById('workflow-template');
        templateSelect.addEventListener('change', () => this.applyTemplate());
        
        updateIcons();

        // Debug log to confirm modal created
        /* eslint-disable no-console */
        console.log('CollaborationModal: modal DOM created successfully');
        /* eslint-enable no-console */
    }

    populateAgentCheckboxes() {
        const container = document.getElementById('agent-checkboxes');
        if (!container) {
            /* eslint-disable no-console */
            console.warn('CollaborationModal: #agent-checkboxes container not found; skipping checkbox population.');
            /* eslint-enable no-console */
            return;
        }
        container.innerHTML = '';
        
        AGENTS.forEach(agent => {
            const label = createElement('label', 'flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors');
            label.innerHTML = `
                <input type="checkbox" id="collab-${agent.id}" class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500">
                <span class="text-sm text-gray-700">${agent.name}</span>
            `;
            container.appendChild(label);
        });
    }

    populateTemplates() {
        const select = document.getElementById('workflow-template');
        if (!select) {
            /* eslint-disable no-console */
            console.warn('CollaborationModal: #workflow-template container not found; skipping template population.');
            /* eslint-enable no-console */
            return;
        }
        select.innerHTML = '<option value="">Select a workflow template...</option>';
        
        this.templates.forEach(template => {
            const option = createElement('option');
            option.value = template.id;
            option.textContent = `${template.name} - ${template.description}`;
            option.dataset.taskDescription = template.task_description;
            option.dataset.taggedAgents = JSON.stringify(template.tagged_agents);
            option.dataset.sequential = template.sequential;
            select.appendChild(option);
        });
    }

    applyTemplate() {
        const select = document.getElementById('workflow-template');
        const selectedOption = select.options[select.selectedIndex];
        
        if (selectedOption.value) {
            // Set task description
            document.getElementById('collab-task').value = selectedOption.dataset.taskDescription;
            
            // Clear all checkboxes first
            AGENTS.forEach(agent => {
                const checkbox = document.getElementById(`collab-${agent.id}`);
                if (checkbox) checkbox.checked = false;
            });
            
            // Select the agents from the template
            const taggedAgents = JSON.parse(selectedOption.dataset.taggedAgents);
            taggedAgents.forEach(agentId => {
                const checkbox = document.getElementById(`collab-${agentId}`);
                if (checkbox) checkbox.checked = true;
            });
        }
    }

    async selectDirectory() {
        const currentDir = document.getElementById('collab-working-dir').value;
        const selectedPath = await this.directoryBrowser.open(currentDir);
        if (selectedPath) {
            document.getElementById('collab-working-dir').value = selectedPath;
            showNotification(`Working directory selected: ${selectedPath}`, 'success');
        }
    }

    async loadWorkflowTemplates() {
        try {
            const data = await this.api.getWorkflowTemplates();
            this.templates = data.templates || [];
        } catch (err) {
            console.error('Error loading workflow templates:', err);
        }
    }

    async startCollaboration() {
        const task = document.getElementById('collab-task').value.trim();
        const workingDir = document.getElementById('collab-working-dir').value.trim();
        const taggedAgents = [];
        
        AGENTS.forEach(agent => {
            const checkbox = document.getElementById(`collab-${agent.id}`);
            if (checkbox && checkbox.checked) {
                taggedAgents.push(agent.id);
            }
        });
        
        // Always include General Assistant for executive summary
        if (!taggedAgents.includes('general_01')) {
            taggedAgents.push('general_01');
            const generalCheckbox = document.getElementById('collab-general_01');
            if (generalCheckbox) generalCheckbox.checked = true;
        }

        if (!task || taggedAgents.length === 0 || !workingDir) {
            showNotification('Please provide a task description, select at least one agent, and specify a working directory.', 'error');
            return;
        }

        const resultsDiv = document.getElementById('collab-results');
        resultsDiv.classList.remove('hidden');
        resultsDiv.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                <span class="text-sm text-gray-600">Starting collaboration...</span>
            </div>
        `;

        try {
            const enhancePrompt = document.getElementById('enhance-prompt-collab').checked;
            const data = await this.api.startCollaboration(task, taggedAgents, workingDir, false, enhancePrompt);
            
            if (data.success) {
                this.activeTaskId = data.task_id;
                
                resultsDiv.innerHTML = `
                    <div class="space-y-3">
                        <div class="flex items-center space-x-2 text-green-600">
                            <i data-lucide="check-circle" class="w-5 h-5"></i>
                            <span class="font-medium">Collaboration started successfully!</span>
                        </div>
                        <div class="text-sm text-gray-600">
                            <p>Task ID: ${data.task_id}</p>
                            <p>Agents: ${taggedAgents.map(id => getAgentById(id).name).join(', ')}</p>
                        </div>
                        <div class="mt-4">
                            <div class="flex items-center justify-between text-sm">
                                <span class="text-gray-600">Progress</span>
                                <span class="font-medium" id="collab-progress">0%</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                                <div id="collab-progress-bar" class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                `;
                updateIcons();
                
                // Show the collaboration chat window
                document.getElementById('collab-chat-window').classList.remove('hidden');
                document.getElementById('collab-chat-area').innerHTML = '<div class="text-center text-gray-500">Waiting for agent responses...</div>';
                
                // Show enhanced progress dashboard
                this.showProgressDashboard(taggedAgents);
                
                // Join WebSocket room
                if (this.wsService) {
                    this.wsService.joinTask(data.task_id);
                }
                
                // Start polling for updates
                this.pollStatus();
                
                showNotification('Tip: You can also view responses in individual agent chat windows', 'info');
            } else {
                resultsDiv.innerHTML = `
                    <div class="flex items-center space-x-2 text-red-600">
                        <i data-lucide="alert-circle" class="w-5 h-5"></i>
                        <span>Error: ${escapeHtml(data.error)}</span>
                    </div>
                `;
                updateIcons();
            }
        } catch (err) {
            resultsDiv.innerHTML = `
                <div class="flex items-center space-x-2 text-red-600">
                    <i data-lucide="alert-circle" class="w-5 h-5"></i>
                    <span>Error: Failed to start collaboration</span>
                </div>
            `;
            updateIcons();
        }
    }

    async pollStatus() {
        if (!this.activeTaskId) return;
        
        try {
            const data = await this.api.getConversation(this.activeTaskId);
            
            if (data.success) {
                // Enhanced progress update with database-backed data
                this.updateProgress({ 
                    progress: data.progress || 0,
                    status: data.status,
                    agent_statuses: data.agent_statuses // New field from database
                });
                this.updateChatArea(data);
                
                // Update timeline with persistent events
                if (data.timeline_events) {
                    data.timeline_events.forEach(event => {
                        this.addTimelineEvent(event.message, event.type, new Date(event.timestamp), event.agent_id);
                    });
                }
                
                // Continue polling if not completed
                if (data.status !== 'completed' && data.status !== 'error') {
                    setTimeout(() => this.pollStatus(), 2000);
                } else {
                    if (data.status === 'completed') {
                        showNotification('Collaboration completed successfully!', 'success');
                        // Mark all working agents as completed
                        const taggedAgents = data.agents || [];
                        taggedAgents.forEach(agentId => {
                            this.updateAgentStatus(agentId, 'completed', 100, 'Task completed successfully');
                        });
                    } else {
                        showNotification('Collaboration encountered an error', 'error');
                    }
                }
            }
        } catch (err) {
            console.error('Error polling collaboration status:', err);
            // Stop polling if task not found - but with database persistence, tasks should persist
            if (err.message && err.message.includes('404')) {
                this.activeTaskId = null;
                showNotification('Task not found. Please check if it was completed or removed.', 'warning');
            }
        }
    }

    updateProgress(data) {
        const progressText = document.getElementById('collab-progress');
        const progressBar = document.getElementById('collab-progress-bar');
        
        if (progressText && data.progress !== undefined) {
            progressText.textContent = `${data.progress}%`;
        }
        if (progressBar && data.progress !== undefined) {
            progressBar.style.width = `${data.progress}%`;
        }
    }

    updateChatArea(data) {
        const chatArea = document.getElementById('collab-chat-area');
        if (!chatArea) return;
        
        const allCommunications = data.all_communications || [];
        
        if (allCommunications.length > 0 || (data.conversations && data.conversations.length > 0)) {
            // Clear loading message if present
            if (chatArea.querySelector('.text-gray-500')) {
                chatArea.innerHTML = '';
            }
            
            // Process communications
            allCommunications.forEach(comm => {
                if (comm.type === 'agent_communication') {
                    this.displayAgentCommunication(comm);
                }
            });
            
            // Process conversations
            if (data.conversations) {
                this.displayConversations(data.conversations);
            }
        }
    }

    displayAgentCommunication(comm) {
        const chatArea = document.getElementById('collab-chat-area');
        const messageId = `agent-comm-${comm.message_id}`;
        
        if (document.getElementById(messageId)) {
            // Update existing message
            const existingDiv = document.getElementById(messageId);
            if (comm.response && !existingDiv.querySelector('.agent-communication-response')) {
                const responseDiv = createElement('div', 'agent-communication-response');
                responseDiv.innerHTML = `<strong>Response:</strong> ${formatAgentResponse(comm.response)}`;
                existingDiv.appendChild(responseDiv);
            }
            return;
        }
        
        const commDiv = createElement('div', 'agent-communication mb-4');
        commDiv.id = messageId;
        commDiv.innerHTML = `
            <div class="agent-communication-header">
                <div class="agent-communication-arrow">
                    <i data-lucide="send" class="w-3 h-3"></i>
                    <span>${comm.from_agent}</span>
                    <i data-lucide="arrow-right" class="w-3 h-3"></i>
                    <span>${comm.to_agent}</span>
                </div>
                <span class="text-xs text-gray-500">${new Date(comm.timestamp).toLocaleTimeString()}</span>
            </div>
            <div class="agent-communication-message">
                <strong>Request:</strong> ${formatAgentResponse(comm.message)}
            </div>
            ${comm.response ? `
            <div class="agent-communication-response">
                <strong>Response:</strong> ${formatAgentResponse(comm.response)}
            </div>
            ` : '<div class="text-sm text-gray-500 italic">Awaiting response...</div>'}
        `;
        
        chatArea.appendChild(commDiv);
        updateIcons();
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    displayConversations(conversations) {
        const chatArea = document.getElementById('collab-chat-area');
        
        // Group by agent
        const agentMessages = {};
        conversations.forEach(conv => {
            const agentId = conv.agent_id;
            if (!agentMessages[agentId]) {
                agentMessages[agentId] = [];
            }
            agentMessages[agentId].push(conv);
        });
        
        Object.keys(agentMessages).forEach(agentName => {
            let messagesToShow = agentMessages[agentName];
            
            // For General Assistant, only show the last message
            if (agentName === 'General Assistant') {
                messagesToShow = [messagesToShow[messagesToShow.length - 1]];
            }
            
            messagesToShow.forEach(conv => {
                const messageId = `collab-msg-${conv.agent_id}-${new Date(conv.timestamp).getTime()}`;
                if (!document.getElementById(messageId)) {
                    const agent = getAgentByName(conv.agent_id);
                    const messageDiv = createElement('div', 'bg-white rounded-lg p-3 shadow-sm border border-gray-200 mb-3');
                    messageDiv.id = messageId;
                    
                    const agentColor = agent ? getAgentColor(agent.color) : 'bg-gray-500';
                    const agentIcon = agent ? agent.icon : 'message-circle';
                    const isExecutiveSummary = conv.agent_id === 'General Assistant' && conv.content.includes('Executive Summary');
                    
                    messageDiv.innerHTML = `
                        <div class="flex items-start space-x-3">
                            <div class="flex-shrink-0 w-8 h-8 ${agentColor} rounded-lg flex items-center justify-center">
                                <i data-lucide="${agentIcon}" class="w-4 h-4 text-white"></i>
                            </div>
                            <div class="flex-1">
                                <div class="flex items-center space-x-2 mb-1">
                                    <span class="font-semibold text-sm text-gray-900">${conv.agent_id}</span>
                                    <span class="text-xs text-gray-500">${new Date(conv.timestamp).toLocaleTimeString()}</span>
                                    ${isExecutiveSummary ? '<span class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Executive Summary</span>' : ''}
                                </div>
                                <div class="bg-gray-50 rounded-lg p-3 border border-gray-200">
                                    <div class="agent-response text-sm">
                                        ${formatAgentResponse(conv.content)}
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    chatArea.appendChild(messageDiv);
                    updateIcons();
                    chatArea.scrollTop = chatArea.scrollHeight;
                }
            });
        });
    }

    handleAgentCommunication(data) {
        const comm = data.communication || data;
        this.displayAgentCommunication(comm);
        showNotification(`${comm.from_agent} is communicating with ${comm.to_agent}`, 'info');
    }

    async handleAgentMention(detail) {
        // This method is kept for backward compatibility
        // The new group chat functionality is handled directly in chat-interface.js
        console.log('Agent mention event received (handled by chat-interface):', detail);
    }

    showProgressDashboard(taggedAgents) {
        const dashboard = document.getElementById('progress-dashboard');
        if (!dashboard) return;

        dashboard.classList.remove('hidden');

        // Initialize agent status cards
        this.initializeAgentStatusCards(taggedAgents);
        
        // Add initial timeline entry
        this.addTimelineEvent('Collaboration started', 'system', new Date());
    }

    initializeAgentStatusCards(taggedAgents) {
        const statusGrid = document.getElementById('agent-status-grid');
        if (!statusGrid) return;

        statusGrid.innerHTML = '';

        taggedAgents.forEach(agentId => {
            const agent = getAgentById(agentId);
            if (!agent) return;

            const agentCard = createElement('div', 'bg-white rounded-lg border border-gray-200 p-4 shadow-sm');
            agentCard.id = `agent-status-${agentId}`;
            
            const agentColor = getAgentColor(agent.color);
            
            agentCard.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center space-x-2">
                        <div class="w-8 h-8 ${agentColor} rounded-lg flex items-center justify-center">
                            <i data-lucide="${agent.icon}" class="w-4 h-4 text-white"></i>
                        </div>
                        <span class="font-medium text-gray-900">${agent.name}</span>
                    </div>
                    <div class="flex items-center space-x-1">
                        <div class="w-2 h-2 rounded-full bg-gray-300" id="status-indicator-${agentId}"></div>
                        <span class="text-xs text-gray-500" id="status-text-${agentId}">Waiting</span>
                    </div>
                </div>
                
                <div class="space-y-2">
                    <div class="flex justify-between text-xs">
                        <span class="text-gray-600">Progress</span>
                        <span id="agent-progress-${agentId}" class="font-medium">0%</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                        <div id="agent-progress-bar-${agentId}" class="${agentColor.replace('bg-', 'bg-')} h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                    </div>
                </div>
                
                <div class="mt-3 text-xs text-gray-600" id="agent-activity-${agentId}">
                    Ready to start...
                </div>
            `;
            
            statusGrid.appendChild(agentCard);
        });
        
        updateIcons();
    }

    updateAgentStatus(agentId, status, progress = null, activity = null) {
        const statusIndicator = document.getElementById(`status-indicator-${agentId}`);
        const statusText = document.getElementById(`status-text-${agentId}`);
        const progressText = document.getElementById(`agent-progress-${agentId}`);
        const progressBar = document.getElementById(`agent-progress-bar-${agentId}`);
        const activityText = document.getElementById(`agent-activity-${agentId}`);

        if (statusIndicator && statusText) {
            switch (status) {
                case 'working':
                    statusIndicator.className = 'w-2 h-2 rounded-full bg-yellow-400 animate-pulse';
                    statusText.textContent = 'Working';
                    break;
                case 'completed':
                    statusIndicator.className = 'w-2 h-2 rounded-full bg-green-400';
                    statusText.textContent = 'Complete';
                    break;
                case 'error':
                    statusIndicator.className = 'w-2 h-2 rounded-full bg-red-400';
                    statusText.textContent = 'Error';
                    break;
                default:
                    statusIndicator.className = 'w-2 h-2 rounded-full bg-gray-300';
                    statusText.textContent = 'Waiting';
            }
        }

        if (progress !== null && progressText && progressBar) {
            progressText.textContent = `${progress}%`;
            progressBar.style.width = `${progress}%`;
        }

        if (activity && activityText) {
            activityText.textContent = activity;
        }
    }

    addTimelineEvent(event, type = 'system', timestamp = new Date(), agentId = null) {
        const timeline = document.getElementById('activity-timeline');
        if (!timeline) return;

        const eventDiv = createElement('div', 'flex items-center space-x-2 text-xs');
        
        let iconClass = 'w-3 h-3 text-gray-500';
        let textClass = 'text-gray-600';
        
        if (type === 'agent') {
            iconClass = 'w-3 h-3 text-blue-500';
            textClass = 'text-blue-700';
        } else if (type === 'error') {
            iconClass = 'w-3 h-3 text-red-500';
            textClass = 'text-red-700';
        } else if (type === 'complete') {
            iconClass = 'w-3 h-3 text-green-500';
            textClass = 'text-green-700';
        }
        
        eventDiv.innerHTML = `
            <div class="flex-shrink-0">
                <i data-lucide="${type === 'agent' ? 'user' : type === 'error' ? 'alert-circle' : type === 'complete' ? 'check-circle' : 'clock'}" class="${iconClass}"></i>
            </div>
            <div class="flex-1 ${textClass}">
                <span>${event}</span>
                ${agentId ? `<span class="text-gray-500"> - ${agentId}</span>` : ''}
            </div>
            <div class="text-gray-400">
                ${timestamp.toLocaleTimeString()}
            </div>
        `;
        
        timeline.appendChild(eventDiv);
        updateIcons();
        
        // Auto-scroll to bottom
        timeline.scrollTop = timeline.scrollHeight;
        
        // Limit timeline to last 10 events
        while (timeline.children.length > 10) {
            timeline.removeChild(timeline.firstChild);
        }
    }

    updateOverallProgress(progress, status = null) {
        const progressText = document.getElementById('overall-progress-text');
        const progressBar = document.getElementById('overall-progress-bar');
        const taskStatus = document.getElementById('task-status');

        if (progressText) {
            progressText.textContent = `${progress}%`;
        }
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        if (status && taskStatus) {
            let statusClass = 'px-3 py-1 text-sm font-medium rounded-full';
            switch (status) {
                case 'running':
                    statusClass += ' bg-blue-100 text-blue-700';
                    taskStatus.textContent = 'In Progress';
                    break;
                case 'completed':
                    statusClass += ' bg-green-100 text-green-700';
                    taskStatus.textContent = 'Completed';
                    break;
                case 'error':
                    statusClass += ' bg-red-100 text-red-700';
                    taskStatus.textContent = 'Error';
                    break;
                default:
                    statusClass += ' bg-gray-100 text-gray-700';
                    taskStatus.textContent = 'Initializing';
            }
            taskStatus.className = statusClass;
        }
    }

    // Enhanced progress update that handles advanced UI features
    updateProgress(data) {
        // Update basic progress bar (legacy)
        const progressText = document.getElementById('collab-progress');
        const progressBar = document.getElementById('collab-progress-bar');
        
        if (progressText && data.progress !== undefined) {
            progressText.textContent = `${data.progress}%`;
        }
        if (progressBar && data.progress !== undefined) {
            progressBar.style.width = `${data.progress}%`;
        }

        // Update advanced dashboard
        this.updateOverallProgress(data.progress || 0, data.status);
        
        // Add timeline event for progress milestones
        if (data.progress && data.progress % 25 === 0 && data.progress > 0) {
            this.addTimelineEvent(`${data.progress}% complete`, 'system');
        }
        
        // Update agent statuses if provided
        if (data.agent_statuses) {
            Object.entries(data.agent_statuses).forEach(([agentId, status]) => {
                this.updateAgentStatus(agentId, status.status, status.progress, status.activity);
            });
        }
    }

    // Enhanced agent communication handler with timeline updates
    handleAgentCommunication(data) {
        const comm = data.communication || data;
        this.displayAgentCommunication(comm);
        
        // Update agent status to working
        this.updateAgentStatus(comm.from_agent, 'working', null, 'Processing request...');
        
        // Add timeline event
        this.addTimelineEvent(`Agent ${comm.from_agent} started working`, 'agent', new Date(), comm.from_agent);
        
        showNotification(`${comm.from_agent} is working on the task`, 'info');
    }
}

//# sourceMappingURL=collaboration-modal.js.map
