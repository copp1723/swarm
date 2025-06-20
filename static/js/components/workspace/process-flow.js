// Process Flow Component - Visualizes agent relationships and task progress
import { createElement, updateIcons } from '../../utils/dom-helpers.js';
import { getAgentById, getAgentColor } from '../../agents/agent-config.js';

export class ProcessFlow {
    constructor() {
        this.activeAgents = [];
        this.agentStatuses = new Map();
        this.connections = new Map();
        this.container = null;
        this.progress = 0;
    }

    init() {
        // Any initialization logic
    }

    render() {
        this.container = createElement('div', 'process-flow');
        
        this.container.innerHTML = `
            <div class="flow-header">
                <div class="flow-title">Task Progress</div>
                <div class="progress-indicator">
                    <span class="progress-text">${this.progress}%</span>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${this.progress}%"></div>
                    </div>
                </div>
            </div>
            
            <div class="agent-flow" id="agent-flow">
                <div class="flow-empty-state">
                    <i data-lucide="git-branch" class="w-12 h-12 text-gray-300"></i>
                    <p>Select agents to see process flow</p>
                </div>
            </div>
            
            <div class="flow-legend">
                <div class="legend-item">
                    <span class="legend-dot ready"></span>
                    <span>Ready</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot working"></span>
                    <span>Working</span>
                </div>
                <div class="legend-item">
                    <span class="legend-dot completed"></span>
                    <span>Completed</span>
                </div>
            </div>
        `;
        
        updateIcons();
        return this.container;
    }

    updateActiveAgents(agentIds) {
        this.activeAgents = agentIds;
        this.renderFlow();
    }

    renderFlow() {
        const flowContainer = this.container.querySelector('#agent-flow');
        
        if (this.activeAgents.length === 0) {
            flowContainer.innerHTML = `
                <div class="flow-empty-state">
                    <i data-lucide="git-branch" class="w-12 h-12 text-gray-300"></i>
                    <p>Select agents to see process flow</p>
                </div>
            `;
            updateIcons();
            return;
        }

        // Create visual flow
        const nodes = this.activeAgents.map((agentId, index) => {
            const agent = getAgentById(agentId);
            if (!agent) return '';
            
            const status = this.agentStatuses.get(agentId) || 'ready';
            const colorClass = getAgentColor(agent.color);
            const isLast = index === this.activeAgents.length - 1;
            
            return `
                <div class="flow-node" data-agent-id="${agentId}">
                    <div class="node-container ${status}">
                        <div class="node-circle ${colorClass}">
                            <i data-lucide="${agent.icon}" class="w-5 h-5 text-white"></i>
                        </div>
                        <div class="node-label">${agent.name}</div>
                        ${status === 'working' ? '<div class="working-pulse"></div>' : ''}
                    </div>
                    ${!isLast ? '<div class="flow-connector"><div class="connector-line"></div></div>' : ''}
                </div>
            `;
        }).join('');

        flowContainer.innerHTML = `
            <div class="flow-nodes">
                ${nodes}
            </div>
        `;
        
        updateIcons();
        this.animateConnections();
    }

    setAgentStatus(agentId, status) {
        this.agentStatuses.set(agentId, status);
        
        const node = this.container.querySelector(`[data-agent-id="${agentId}"] .node-container`);
        if (node) {
            node.classList.remove('ready', 'working', 'completed', 'error');
            node.classList.add(status);
            
            if (status === 'working') {
                // Add working animation
                if (!node.querySelector('.working-pulse')) {
                    const pulse = createElement('div', 'working-pulse');
                    node.appendChild(pulse);
                }
            } else {
                // Remove working animation
                const pulse = node.querySelector('.working-pulse');
                if (pulse) pulse.remove();
            }
        }
        
        // Update progress based on completed agents
        this.updateProgressFromStatuses();
    }

    updateProgressFromStatuses() {
        if (this.activeAgents.length === 0) return;
        
        const completed = Array.from(this.agentStatuses.values())
            .filter(status => status === 'completed').length;
        const total = this.activeAgents.length;
        
        this.progress = Math.round((completed / total) * 100);
        this.updateProgressDisplay();
    }

    updateProgress(progress) {
        this.progress = progress;
        this.updateProgressDisplay();
    }

    updateProgressDisplay() {
        const progressText = this.container.querySelector('.progress-text');
        const progressFill = this.container.querySelector('.progress-fill');
        
        if (progressText) progressText.textContent = `${this.progress}%`;
        if (progressFill) progressFill.style.width = `${this.progress}%`;
    }

    showCommunication(fromAgentId, toAgentId) {
        // Find the nodes
        const fromNode = this.container.querySelector(`[data-agent-id="${fromAgentId}"]`);
        const toNode = this.container.querySelector(`[data-agent-id="${toAgentId}"]`);
        
        if (fromNode && toNode) {
            // Create communication animation
            const fromRect = fromNode.getBoundingClientRect();
            const toRect = toNode.getBoundingClientRect();
            const containerRect = this.container.getBoundingClientRect();
            
            const pulse = createElement('div', 'communication-pulse');
            pulse.style.left = `${fromRect.left - containerRect.left + fromRect.width / 2}px`;
            pulse.style.top = `${fromRect.top - containerRect.top + fromRect.height / 2}px`;
            
            this.container.appendChild(pulse);
            
            // Animate to target
            setTimeout(() => {
                pulse.style.transform = `translate(${toRect.left - fromRect.left}px, ${toRect.top - fromRect.top}px)`;
            }, 10);
            
            // Remove after animation
            setTimeout(() => pulse.remove(), 1000);
        }
        
        // Store connection
        const key = `${fromAgentId}->${toAgentId}`;
        this.connections.set(key, Date.now());
    }

    animateConnections() {
        const connectors = this.container.querySelectorAll('.connector-line');
        connectors.forEach((connector, index) => {
            setTimeout(() => {
                connector.classList.add('active');
            }, index * 100);
        });
    }

    reset() {
        this.activeAgents = [];
        this.agentStatuses.clear();
        this.connections.clear();
        this.progress = 0;
        
        if (this.container) {
            this.renderFlow();
            this.updateProgressDisplay();
        }
    }
}
