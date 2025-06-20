// @ts-check
// Agent Manager - handles all agent instances and coordination
import { AGENTS, getAgentColor } from './agent-config.js';
import { ChatInterface } from '../components/chat-interface.js';
import { createElement, updateIcons } from '../utils/dom-helpers.js';
import { getAuthHeaders } from '../config.js';

/**
 * Manages all agent instances and their coordination
 * Handles sidebar navigation, chat interfaces, and agent state management
 * Follows Core Development Rules for modular structure and dependency injection
 */
export class AgentManager {
    constructor() {
        /** @type {Array<any>} List of available agents */
        this.agents = [];
        /** @type {Map<string, ChatInterface>} Map of agent IDs to chat interfaces */
        this.chatInterfaces = new Map();
        /** @type {string|null} Currently selected agent ID */
        this.currentAgentId = null;
        /** @type {HTMLElement|null} Sidebar element */
        this.sidebar = null;
        /** @type {HTMLElement|null} Main container element */
        this.container = null;
    }

    /**
     * Initialize the agent manager with async agent loading
     * Sets up sidebar, containers, and event listeners
     * @returns {Promise<void>}
     */
    async init() {
        await this.loadAgents();
        this.initializeSidebar();
        this.initializeAgentContainers();
        this.setupEventListeners();
        updateIcons();
    }

    /**
     * Load agents from API with fallback to hardcoded configuration
     * Implements error handling and resilience patterns per Core Development Rules
     * @returns {Promise<void>}
     */
    async loadAgents() {
        try {
            const response = await fetch('/api/agents/list', {
                headers: getAuthHeaders()
            });
            const data = await response.json();
            
            if (data.success) {
                // Transform API response to match UI format, use backend-provided agent_id
                this.agents = data.profiles.map(profile => {
                    return {
                        id: profile.agent_id || profile.id || profile.name.toLowerCase().replace(/\s+/g, '_') + '_01',
                        name: profile.name,
                        role: profile.description || profile.role,
                        icon: this.getIconForRole(profile.role),
                        color: this.getColorForRole(profile.role)
                    };
                });
            } else {
                console.error('Failed to load agents:', data);
                // Fallback to hardcoded agents
                this.agents = AGENTS;
            }
        } catch (error) {
            console.error('Error loading agents:', error);
            // Fallback to hardcoded agents
            this.agents = AGENTS;
        }
    }

    /**
     * Get Lucide icon name for agent role
     * @param {string} role - The agent role
     * @returns {string} Lucide icon name
     */
    getIconForRole(role) {
        if (role === 'product') return 'package';
        if (role === 'developer') return 'code';
        if (role === 'qa') return 'bug';
        return 'message-circle';
    }

    /**
     * Get color scheme for agent role
     * @param {string} role - The agent role
     * @returns {string} Color name for UI theming
     */
    getColorForRole(role) {
        if (role === 'product') return 'purple';
        if (role === 'developer') return 'green';
        if (role === 'qa') return 'red';
        return 'gray';
    }

    initializeSidebar() {
        const navList = document.getElementById('agent-nav-list');
        navList.innerHTML = '';
        
        this.agents.forEach(agent => {
            const navItem = createElement('div', 'agent-nav-item');
            navItem.id = `nav-${agent.id}`;
            
            const colorClass = getAgentColor(agent.color);
            navItem.innerHTML = `
                <div class="flex items-center flex-1">
                    <div class="w-10 h-10 ${colorClass} rounded-lg flex items-center justify-center mr-3">
                        <i data-lucide="${agent.icon}" class="w-5 h-5 text-white"></i>
                    </div>
                    <div>
                        <div class="font-medium">${agent.name}</div>
                        <div class="text-xs text-gray-400">${agent.role.substring(0, 30)}...</div>
                    </div>
                </div>
                <div class="status-indicator w-2 h-2 rounded-full bg-gray-500"></div>
            `;
            
            navItem.addEventListener('click', () => this.selectAgent(agent.id));
            navList.appendChild(navItem);
        });
    }

    initializeAgentContainers() {
        this.container = document.getElementById('agent-chats-container');
        
        // Create chat interfaces for all agents
        this.agents.forEach(agent => {
            const chatInterface = new ChatInterface(agent.id);
            const chatContainer = chatInterface.render();
            this.container.appendChild(chatContainer);
            this.chatInterfaces.set(agent.id, chatInterface);
        });
    }

    setupEventListeners() {
        // Mobile menu toggle
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', () => this.toggleMobileSidebar());
        }
        
        // Sidebar collapse
        const collapseBtn = document.getElementById('collapse-sidebar');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => this.toggleSidebar());
        }
        
        // Listen for agent mentions (three-way chat)
        document.addEventListener('agent-mention', (event) => {
            this.handleAgentMention(event.detail);
        });
    }

    selectAgent(agentId) {
        // Hide welcome message
        const welcomeMsg = document.getElementById('welcome-message');
        if (welcomeMsg) welcomeMsg.style.display = 'none';
        
        // Update sidebar active state
        document.querySelectorAll('.agent-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.getElementById(`nav-${agentId}`).classList.add('active');
        
        // Hide all chat interfaces
        this.chatInterfaces.forEach((chatInterface, id) => {
            if (id === agentId) {
                chatInterface.show();
            } else {
                chatInterface.hide();
            }
        });
        
        // Update header
        const agent = this.agents.find(a => a.id === agentId);
        const currentAgentName = document.getElementById('current-agent-name');
        const currentAgentStatus = document.getElementById('current-agent-status');
        
        if (currentAgentName) currentAgentName.textContent = agent.name;
        if (currentAgentStatus) {
            currentAgentStatus.textContent = agent.id.split('_')[0].toUpperCase();
            currentAgentStatus.className = `px-3 py-1 text-xs font-medium rounded-full bg-${agent.color}-100 text-${agent.color}-700`;
        }
        
        this.currentAgentId = agentId;
        
        // Close mobile sidebar
        if (window.innerWidth < 768) {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) sidebar.classList.remove('open');
        }
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        
        if (!sidebar || !mainContent) return;
        
        sidebar.classList.toggle('collapsed');
        mainContent.classList.toggle('full-width');
        
        // Update collapse button
        const collapseBtn = document.getElementById('collapse-sidebar');
        if (collapseBtn) {
            const icon = collapseBtn.querySelector('i');
            const text = collapseBtn.querySelector('span');
            
            if (sidebar.classList.contains('collapsed')) {
                icon.setAttribute('data-lucide', 'chevron-right');
                text.textContent = 'Expand';
            } else {
                icon.setAttribute('data-lucide', 'chevron-left');
                text.textContent = 'Collapse';
            }
            
            updateIcons();
        }
    }

    toggleMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
    }

    handleAgentMention(detail) {
        // This will be handled by the collaboration modal
        const event = new CustomEvent('start-three-way-chat', { detail });
        document.dispatchEvent(event);
    }

    updateAgentStatus(agentId, isActive) {
        const navItem = document.getElementById(`nav-${agentId}`);
        if (navItem) {
            const indicator = navItem.querySelector('.status-indicator');
            if (indicator) {
                if (isActive) {
                    indicator.classList.remove('bg-gray-500');
                    indicator.classList.add('bg-green-500');
                } else {
                    indicator.classList.remove('bg-green-500');
                    indicator.classList.add('bg-gray-500');
                }
            }
        }
        
        // Also update the chat interface status
        const chatInterface = this.chatInterfaces.get(agentId);
        if (chatInterface) {
            chatInterface.updateStatus(isActive);
        }
    }

    getAgent(agentId) {
        return this.agents.find(a => a.id === agentId);
    }

    getChatInterface(agentId) {
        return this.chatInterfaces.get(agentId);
    }

    getAllAgents() {
        return this.agents;
    }
}
//# sourceMappingURL=agent-manager.js.map
