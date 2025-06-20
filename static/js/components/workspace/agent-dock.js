// Agent Dock Component - Visual agent selector with status indicators
import { createElement, updateIcons } from '../../utils/dom-helpers.js';
import { AGENTS, getAgentColor } from '../../agents/agent-config.js';

export class AgentDock {
    constructor() {
        this.selectedAgents = new Set();
        this.agentStatuses = new Map();
        this.onSelectionChange = null;
        this.container = null;
    }

    init(onSelectionChange) {
        this.onSelectionChange = onSelectionChange;
        
        // Initialize all agents as ready
        AGENTS.forEach(agent => {
            this.agentStatuses.set(agent.id, 'ready');
        });
    }

    render() {
        this.container = createElement('div', 'agent-dock');
        
        this.container.innerHTML = `
            <div class="dock-header">
                <h2 class="dock-title">Available Agents</h2>
                <p class="dock-subtitle">Click to add agents to your workspace</p>
            </div>
            
            <div class="agent-grid" id="agent-grid">
                ${this.renderAgentTiles()}
            </div>
            
            <div class="dock-actions">
                <button class="select-all-btn" id="select-all-agents">
                    <i data-lucide="users" class="w-4 h-4"></i>
                    Select All
                </button>
            </div>
        `;
        
        this.attachEventListeners();
        updateIcons();
        
        return this.container;
    }

    renderAgentTiles() {
        return AGENTS.map(agent => {
            const colorClass = getAgentColor(agent.color);
            const status = this.agentStatuses.get(agent.id) || 'ready';
            const isSelected = this.selectedAgents.has(agent.id);
            
            return `
                <div class="agent-tile ${isSelected ? 'selected' : ''} ${status}" 
                     data-agent-id="${agent.id}"
                     role="button"
                     tabindex="0">
                    <div class="tile-header">
                        <div class="agent-avatar ${colorClass}">
                            <i data-lucide="${agent.icon}" class="w-5 h-5 text-white"></i>
                        </div>
                        <div class="status-indicator ${status}"></div>
                    </div>
                    
                    <div class="tile-content">
                        <h3 class="agent-name">${agent.name}</h3>
                        <p class="agent-role">${agent.role}</p>
                    </div>
                    
                    <div class="tile-footer">
                        <span class="status-text">${this.getStatusText(status)}</span>
                    </div>
                    
                    <div class="selection-overlay">
                        <i data-lucide="check" class="w-6 h-6"></i>
                    </div>
                </div>
            `;
        }).join('');
    }

    attachEventListeners() {
        // Agent tile clicks
        const tiles = this.container.querySelectorAll('.agent-tile');
        tiles.forEach(tile => {
            tile.addEventListener('click', () => this.toggleAgent(tile.dataset.agentId));
            
            // Keyboard accessibility
            tile.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleAgent(tile.dataset.agentId);
                }
            });
        });
        
        // Select all button
        const selectAllBtn = this.container.querySelector('#select-all-agents');
        selectAllBtn.addEventListener('click', () => this.selectAllAgents());
    }

    toggleAgent(agentId) {
        const isSelected = this.selectedAgents.has(agentId);
        
        if (isSelected) {
            this.selectedAgents.delete(agentId);
        } else {
            this.selectedAgents.add(agentId);
        }
        
        // Update UI
        const tile = this.container.querySelector(`[data-agent-id="${agentId}"]`);
        if (tile) {
            tile.classList.toggle('selected', !isSelected);
        }
        
        // Notify parent component
        if (this.onSelectionChange) {
            this.onSelectionChange(agentId, !isSelected);
        }
    }

    setAgentActive(agentId, active) {
        if (active) {
            this.selectedAgents.add(agentId);
        } else {
            this.selectedAgents.delete(agentId);
        }
        
        const tile = this.container.querySelector(`[data-agent-id="${agentId}"]`);
        if (tile) {
            tile.classList.toggle('selected', active);
        }
    }

    updateAgentStatus(agentId, status) {
        this.agentStatuses.set(agentId, status);
        
        const tile = this.container.querySelector(`[data-agent-id="${agentId}"]`);
        if (tile) {
            // Remove all status classes
            tile.classList.remove('ready', 'working', 'completed', 'error');
            tile.classList.add(status);
            
            // Update status indicator
            const indicator = tile.querySelector('.status-indicator');
            if (indicator) {
                indicator.className = `status-indicator ${status}`;
            }
            
            // Update status text
            const statusText = tile.querySelector('.status-text');
            if (statusText) {
                statusText.textContent = this.getStatusText(status);
            }
        }
    }

    selectAllAgents() {
        const allSelected = this.selectedAgents.size === AGENTS.length;
        
        if (allSelected) {
            // Deselect all
            this.selectedAgents.clear();
            AGENTS.forEach(agent => {
                const tile = this.container.querySelector(`[data-agent-id="${agent.id}"]`);
                if (tile) tile.classList.remove('selected');
                if (this.onSelectionChange) {
                    this.onSelectionChange(agent.id, false);
                }
            });
        } else {
            // Select all
            AGENTS.forEach(agent => {
                if (!this.selectedAgents.has(agent.id)) {
                    this.selectedAgents.add(agent.id);
                    const tile = this.container.querySelector(`[data-agent-id="${agent.id}"]`);
                    if (tile) tile.classList.add('selected');
                    if (this.onSelectionChange) {
                        this.onSelectionChange(agent.id, true);
                    }
                }
            });
        }
        
        // Update button text
        const btn = this.container.querySelector('#select-all-agents');
        if (btn) {
            btn.innerHTML = allSelected ? 
                '<i data-lucide="users" class="w-4 h-4"></i> Select All' :
                '<i data-lucide="users-x" class="w-4 h-4"></i> Deselect All';
            updateIcons();
        }
    }

    clearSelections() {
        this.selectedAgents.clear();
        const tiles = this.container.querySelectorAll('.agent-tile');
        tiles.forEach(tile => tile.classList.remove('selected'));
        
        // Reset all statuses
        AGENTS.forEach(agent => {
            this.updateAgentStatus(agent.id, 'ready');
        });
    }

    getStatusText(status) {
        const statusMap = {
            'ready': 'Ready',
            'working': 'Working...',
            'completed': 'Completed',
            'error': 'Error'
        };
        return statusMap[status] || 'Unknown';
    }
}
