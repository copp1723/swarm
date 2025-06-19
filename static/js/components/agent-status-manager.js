// Agent Status Manager for Real-time UI Updates
import { createElement, updateIcons } from '../utils/dom-helpers.js';

export class AgentStatusManager {
    constructor() {
        this.agentStates = new Map();
        this.statusUpdateCallbacks = new Map();
    }

    init() {
        this.setupGlobalAgentIndicators();
        this.setupStatusObserver();
    }

    setupGlobalAgentIndicators() {
        // Enhanced sidebar agent status indicators
        const agentNavItems = document.querySelectorAll('.agent-nav-item');
        
        agentNavItems.forEach(navItem => {
            const agentId = this.extractAgentIdFromElement(navItem);
            if (!agentId) return;

            // Add enhanced status indicator if not already present
            let statusContainer = navItem.querySelector('.agent-status-container');
            if (!statusContainer) {
                statusContainer = createElement('div', 'agent-status-container flex items-center space-x-1');
                
                // Create status indicator
                const statusIndicator = createElement('div', 'status-indicator w-2 h-2 rounded-full bg-gray-400');
                statusIndicator.id = `sidebar-status-${agentId}`;
                
                // Create activity text
                const activityText = createElement('span', 'activity-text text-xs text-gray-500 hidden');
                activityText.id = `sidebar-activity-${agentId}`;
                
                statusContainer.appendChild(statusIndicator);
                statusContainer.appendChild(activityText);
                
                // Add to the nav item
                const existingStatus = navItem.querySelector('.status-indicator');
                if (existingStatus) {
                    existingStatus.parentNode.replaceChild(statusContainer, existingStatus);
                } else {
                    navItem.appendChild(statusContainer);
                }
            }

            // Initialize agent state
            this.agentStates.set(agentId, {
                status: 'idle',
                activity: null,
                lastUpdate: Date.now()
            });
        });

        updateIcons();
    }

    setupStatusObserver() {
        // Create floating status panel for active agents
        const statusPanel = this.createFloatingStatusPanel();
        document.body.appendChild(statusPanel);
        
        // Auto-hide panel when no agents are active
        setInterval(() => {
            this.updateFloatingPanel();
        }, 1000);
    }

    createFloatingStatusPanel() {
        const panel = createElement('div', 'fixed top-20 right-4 bg-white rounded-lg shadow-lg border border-gray-200 p-4 max-w-sm z-40 transform translate-x-full transition-transform duration-300');
        panel.id = 'floating-agent-status';
        
        panel.innerHTML = `
            <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-semibold text-gray-900 flex items-center">
                    <i data-lucide="activity" class="w-4 h-4 mr-2 text-blue-600"></i>
                    Agent Activity
                </h4>
                <button id="hide-status-panel" class="text-gray-400 hover:text-gray-600">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>
            <div id="active-agents-list" class="space-y-2">
                <!-- Active agents will be populated here -->
            </div>
        `;

        // Hide panel button
        panel.querySelector('#hide-status-panel').addEventListener('click', () => {
            this.hideFloatingPanel();
        });

        updateIcons();
        return panel;
    }

    updateAgentStatus(agentId, status, activity = null, progress = null) {
        // Update agent state
        this.agentStates.set(agentId, {
            status,
            activity,
            progress,
            lastUpdate: Date.now()
        });

        // Update sidebar indicator
        this.updateSidebarStatus(agentId, status, activity);
        
        // Update floating panel
        this.updateFloatingPanel();
        
        // Trigger callbacks
        const callbacks = this.statusUpdateCallbacks.get(agentId) || [];
        callbacks.forEach(callback => {
            try {
                callback({ agentId, status, activity, progress });
            } catch (error) {
                console.error('Error in agent status callback:', error);
            }
        });
    }

    updateSidebarStatus(agentId, status, activity) {
        const statusIndicator = document.getElementById(`sidebar-status-${agentId}`);
        const activityText = document.getElementById(`sidebar-activity-${agentId}`);
        
        if (!statusIndicator) return;

        // Reset classes
        statusIndicator.className = 'status-indicator w-2 h-2 rounded-full';
        
        // Update status indicator
        switch (status) {
            case 'idle':
                statusIndicator.classList.add('bg-gray-400');
                break;
            case 'working':
                statusIndicator.classList.add('bg-yellow-400', 'animate-pulse');
                break;
            case 'completed':
                statusIndicator.classList.add('bg-green-400');
                // Auto-reset to idle after 3 seconds
                setTimeout(() => {
                    if (this.agentStates.get(agentId)?.status === 'completed') {
                        this.updateAgentStatus(agentId, 'idle');
                    }
                }, 3000);
                break;
            case 'error':
                statusIndicator.classList.add('bg-red-400');
                // Auto-reset to idle after 5 seconds
                setTimeout(() => {
                    if (this.agentStates.get(agentId)?.status === 'error') {
                        this.updateAgentStatus(agentId, 'idle');
                    }
                }, 5000);
                break;
        }

        // Update activity text
        if (activityText) {
            if (activity && status !== 'idle') {
                activityText.textContent = activity;
                activityText.classList.remove('hidden');
            } else {
                activityText.classList.add('hidden');
            }
        }

        // Add tooltip with agent name and status
        const navItem = statusIndicator.closest('.agent-nav-item');
        if (navItem) {
            const statusText = this.getStatusText(status, activity);
            navItem.title = statusText;
        }
    }

    updateFloatingPanel() {
        const panel = document.getElementById('floating-agent-status');
        const activeAgentsList = document.getElementById('active-agents-list');
        
        if (!panel || !activeAgentsList) return;

        // Get active agents
        const activeAgents = Array.from(this.agentStates.entries())
            .filter(([agentId, state]) => state.status !== 'idle' && (Date.now() - state.lastUpdate) < 10000)
            .sort(([, a], [, b]) => b.lastUpdate - a.lastUpdate);

        if (activeAgents.length === 0) {
            this.hideFloatingPanel();
            return;
        }

        // Show panel
        panel.classList.remove('translate-x-full');
        panel.classList.add('translate-x-0');

        // Update agent list
        activeAgentsList.innerHTML = activeAgents.map(([agentId, state]) => {
            const statusColor = this.getStatusColor(state.status);
            const statusText = this.getStatusText(state.status, state.activity);
            
            return `
                <div class="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg">
                    <div class="w-2 h-2 rounded-full ${statusColor} ${state.status === 'working' ? 'animate-pulse' : ''}"></div>
                    <div class="flex-1">
                        <div class="text-sm font-medium text-gray-900">${agentId}</div>
                        <div class="text-xs text-gray-600">${statusText}</div>
                        ${state.progress !== null ? `
                            <div class="w-full bg-gray-200 rounded-full h-1 mt-1">
                                <div class="bg-blue-500 h-1 rounded-full transition-all duration-300" style="width: ${state.progress}%"></div>
                            </div>
                        ` : ''}
                    </div>
                    <div class="text-xs text-gray-400">
                        ${this.getTimeAgo(state.lastUpdate)}
                    </div>
                </div>
            `;
        }).join('');
    }

    hideFloatingPanel() {
        const panel = document.getElementById('floating-agent-status');
        if (panel) {
            panel.classList.remove('translate-x-0');
            panel.classList.add('translate-x-full');
        }
    }

    getStatusColor(status) {
        switch (status) {
            case 'working': return 'bg-yellow-400';
            case 'completed': return 'bg-green-400';
            case 'error': return 'bg-red-400';
            default: return 'bg-gray-400';
        }
    }

    getStatusText(status, activity) {
        if (activity) {
            return activity;
        }
        
        switch (status) {
            case 'working': return 'Processing...';
            case 'completed': return 'Task completed';
            case 'error': return 'Error occurred';
            default: return 'Ready';
        }
    }

    getTimeAgo(timestamp) {
        const seconds = Math.floor((Date.now() - timestamp) / 1000);
        if (seconds < 60) return `${seconds}s ago`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    }

    extractAgentIdFromElement(element) {
        // Try to extract agent ID from element ID or data attributes
        if (element.id && element.id.startsWith('nav-')) {
            return element.id.replace('nav-', '');
        }
        
        if (element.dataset.agentId) {
            return element.dataset.agentId;
        }

        // Try to find agent ID in child elements
        const agentIdElement = element.querySelector('[data-agent-id]');
        if (agentIdElement) {
            return agentIdElement.dataset.agentId;
        }

        return null;
    }

    // Subscribe to agent status updates
    onAgentStatusUpdate(agentId, callback) {
        if (!this.statusUpdateCallbacks.has(agentId)) {
            this.statusUpdateCallbacks.set(agentId, []);
        }
        this.statusUpdateCallbacks.get(agentId).push(callback);
    }

    // Unsubscribe from agent status updates
    offAgentStatusUpdate(agentId, callback) {
        const callbacks = this.statusUpdateCallbacks.get(agentId);
        if (callbacks) {
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    // Get current status of an agent
    getAgentStatus(agentId) {
        return this.agentStates.get(agentId) || { status: 'idle', activity: null, progress: null };
    }

    // Get all agent statuses
    getAllAgentStatuses() {
        return Object.fromEntries(this.agentStates);
    }

    // Reset all agent statuses
    resetAllAgentStatuses() {
        this.agentStates.clear();
        this.setupGlobalAgentIndicators();
        this.hideFloatingPanel();
    }

    // Simulate agent activity for demo purposes
    simulateAgentActivity(agentId, duration = 5000) {
        this.updateAgentStatus(agentId, 'working', 'Simulating work...');
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 25;
            if (progress >= 100) {
                progress = 100;
                this.updateAgentStatus(agentId, 'completed', 'Task completed', progress);
                clearInterval(interval);
            } else {
                this.updateAgentStatus(agentId, 'working', 'Processing...', Math.round(progress));
            }
        }, duration / 10);
    }
}

