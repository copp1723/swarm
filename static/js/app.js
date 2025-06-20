// Main Application Entry Point
import { AgentManager } from './agents/agent-manager.js';
import { CollaborationModal } from './components/collaboration-modal.js';
import { WorkflowVisualization } from './components/workflow-visualization.js';
import { AgentStatusManager } from './components/agent-status-manager.js';
import { WebSocketService } from './services/websocket.js';
import { StorageService } from './services/storage.js';
import { showNotification } from './utils/dom-helpers.js';
import { initApiKeySetup, showProviderWarning, updateUIForProviderStatus } from './components/api-key-setup.js';
import { apiClient } from './services/api-client.js';
import { darkModeManager } from './utils/dark-mode.js';
import { dragDropManager } from './utils/drag-drop.js';
import { mentionAutocomplete } from './utils/mention-autocomplete.js';

class App {
    constructor() {
        this.agentManager = new AgentManager();
        this.wsService = new WebSocketService();
        this.storage = new StorageService();
        this.collaborationModal = null;
        this.workflowVisualization = new WorkflowVisualization();
        this.agentStatusManager = new AgentStatusManager(this.wsService);
    }

    async init() {
        try {
            // Initialize API key setup if needed
            initApiKeySetup();
            
            // Check provider configuration and update UI accordingly
            await this.checkProviderConfiguration();
            
            // Initialize core components
            await this.agentManager.init();
            
            // Initialize advanced UI features
            this.initializeAdvancedFeatures();
            
            // Initialize WebSocket
            this.wsService.connect();
            
            // Initialize collaboration modal
            this.collaborationModal = new CollaborationModal(this.agentManager, this.wsService);
            await this.collaborationModal.init();
            
            // Initialize advanced UI features
            this.agentStatusManager.init();
            
            // Setup WebSocket listeners for advanced features
            this.setupAdvancedWebSocketListeners();
            
            // Setup global event listeners
            this.setupGlobalListeners();
            
            // Load preferences
            this.loadGlobalPreferences();
            
            // Set up periodic health checks
            this.setupHealthChecks();
            
            // Show welcome notification
            showNotification('MCP Agent Chat Interface loaded successfully', 'success');
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            showNotification('Failed to initialize application', 'error');
        }
    }

    setupAdvancedWebSocketListeners() {
        // Listen for agent communication events to update status
        this.wsService.on('agent_communication', (data) => {
            const agentId = data.from_agent || data.communication?.from_agent;
            if (agentId) {
                this.agentStatusManager.updateAgentStatus(agentId, 'working', 'Communicating...');
            }
        });
        
        // Listen for task progress events
        this.wsService.on('task_progress', (data) => {
            // Update individual agent statuses if provided
            if (data.agent_statuses) {
                Object.entries(data.agent_statuses).forEach(([agentId, status]) => {
                    this.agentStatusManager.updateAgentStatus(
                        agentId,
                        status.status,
                        status.activity,
                        status.progress
                    );
                });
            }
        });
        
        // Listen for task completion
        this.wsService.on('task_complete', (data) => {
            // Mark all agents as completed
            const allStatuses = this.agentStatusManager.getAllAgentStatuses();
            Object.keys(allStatuses).forEach(agentId => {
                if (allStatuses[agentId].status === 'working') {
                    this.agentStatusManager.updateAgentStatus(agentId, 'completed', 'Task completed');
                }
            });
        });
        
        // Listen for task errors
        this.wsService.on('task_error', (data) => {
            // Mark relevant agents as error state
            showNotification('Task error occurred', 'error');
        });
    }

    setupGlobalListeners() {
        // Global enhance prompt toggle
        const enhanceToggle = document.getElementById('enhance-prompt-global');
        if (enhanceToggle) {
            enhanceToggle.addEventListener('change', (e) => {
                this.storage.setEnhancePromptSetting(e.target.checked);
            });
        }
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K to focus on current agent's input
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                const currentAgent = this.agentManager.currentAgentId;
                if (currentAgent) {
                    const input = document.getElementById(`input-${currentAgent}`);
                    if (input) input.focus();
                }
            }
            
            // Esc to close modals
            if (e.key === 'Escape') {
                if (this.collaborationModal && this.collaborationModal.modal && !this.collaborationModal.modal.classList.contains('hidden')) {
                    this.collaborationModal.close();
                }
            }
        });
        
        // Mobile menu toggle
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        if (mobileMenuBtn) {
            mobileMenuBtn.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    sidebar.classList.toggle('open');
                    // Update button icon
                    const icon = mobileMenuBtn.querySelector('i');
                    if (sidebar.classList.contains('open')) {
                        icon.setAttribute('data-lucide', 'x');
                    } else {
                        icon.setAttribute('data-lucide', 'menu');
                    }
                    // Refresh lucide icons
                    if (typeof lucide !== 'undefined') {
                        lucide.createIcons();
                    }
                }
            });
        }
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            const sidebar = document.getElementById('sidebar');
            const mobileMenuBtn = document.getElementById('mobile-menu-btn');
            
            if (window.innerWidth < 768 && sidebar && sidebar.classList.contains('open')) {
                if (!sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                    sidebar.classList.remove('open');
                    const icon = mobileMenuBtn.querySelector('i');
                    icon.setAttribute('data-lucide', 'menu');
                    if (typeof lucide !== 'undefined') {
                        lucide.createIcons();
                    }
                }
            }
        });
        
        // Handle window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.handleResize();
            }, 250);
        });
    }

    loadGlobalPreferences() {
        // Load enhance prompt setting
        const enhanceToggle = document.getElementById('enhance-prompt-global');
        if (enhanceToggle) {
            enhanceToggle.checked = this.storage.getEnhancePromptSetting();
        }
    }

    handleResize() {
        // Handle responsive behavior
        if (window.innerWidth < 768) {
            // Mobile view - ensure sidebar is closed by default
            const sidebar = document.getElementById('sidebar');
            if (sidebar && !sidebar.classList.contains('collapsed')) {
                sidebar.classList.remove('open');
            }
        }
    }

    // Public API for extensions
    getAgentManager() {
        return this.agentManager;
    }

    getWebSocketService() {
        return this.wsService;
    }

    getStorageService() {
        return this.storage;
    }

    /**
     * Check and handle provider configuration status
     */
    /**
     * Initialize advanced UI features like drag-drop and mentions
     */
    initializeAdvancedFeatures() {
        // Setup drag and drop for agent workspace
        const workspaceContainer = document.getElementById('agent-chats-container');
        if (workspaceContainer) {
            dragDropManager.setupWorkspaceDropZones(workspaceContainer);
        }
        
        // Listen for agent list updates to enable drag-drop on agent items
        document.addEventListener('agentsLoaded', (event) => {
            const agents = event.detail.agents;
            
            // Register agents for mention autocomplete
            mentionAutocomplete.registerAgents(agents);
            
            // Enable drag-drop on agent navigation items
            agents.forEach(agent => {
                const agentNavItem = document.querySelector(`[data-agent-id="${agent.role}"]`);
                if (agentNavItem) {
                    dragDropManager.enableAgentDragging(agent.role, agentNavItem);
                }
            });
        });
        
        // Listen for new chat inputs to enable mention autocomplete
        document.addEventListener('chatInputCreated', (event) => {
            const inputElement = event.detail.inputElement;
            if (inputElement) {
                mentionAutocomplete.enableFor(inputElement);
            }
        });
        
        // Global drag-drop event listeners
        document.addEventListener('agentDropped', (event) => {
            const { agent_id, position, name } = event.detail;
            this.handleAgentWorkspaceDrop(agent_id, position, name);
        });
        
        document.addEventListener('agentCollaboration', (event) => {
            const { source, target, type } = event.detail;
            this.handleAgentCollaboration(source, target, type);
        });
        
        // Add keyboard shortcuts for agent switching
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + 1-9 to switch between agents
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '9') {
                e.preventDefault();
                const agentIndex = parseInt(e.key) - 1;
                const agentProfiles = this.agentManager.agentProfiles;
                if (agentProfiles && agentProfiles[agentIndex]) {
                    this.agentManager.selectAgent(agentProfiles[agentIndex].role);
                }
            }
        });
    }
    
    /**
     * Handle agent dropped into workspace
     * @param {string} agentId 
     * @param {Object} position 
     * @param {string} name 
     */
    handleAgentWorkspaceDrop(agentId, position, name) {
        // Auto-select the dropped agent
        this.agentManager.selectAgent(agentId);
        
        // Show success notification
        showNotification(`${name} is now active in the workspace`, 'success');
        
        // Optional: Auto-focus the input for immediate interaction
        setTimeout(() => {
            const input = document.getElementById(`input-${agentId}`);
            if (input) {
                input.focus();
                input.placeholder = 'Start chatting with ' + name + '...';
            }
        }, 500);
    }
    
    /**
     * Handle agent collaboration events
     * @param {string} sourceAgentId 
     * @param {string} targetAgentId 
     * @param {string} type 
     */
    handleAgentCollaboration(sourceAgentId, targetAgentId, type) {
        if (type === 'chat_handoff') {
            // Get the current message from source agent if any
            const sourceInput = document.getElementById(`input-${sourceAgentId}`);
            const targetInput = document.getElementById(`input-${targetAgentId}`);
            
            if (sourceInput && targetInput && sourceInput.value.trim()) {
                const message = sourceInput.value.trim();
                
                // Add handoff prefix to target input
                targetInput.value = `@${sourceAgentId} handed this off: "${message}"`;
                sourceInput.value = ''; // Clear source
                
                // Switch to target agent
                this.agentManager.selectAgent(targetAgentId);
                targetInput.focus();
                
                showNotification(`Conversation handed off from ${sourceAgentId} to ${targetAgentId}`, 'info');
            }
        }
    }

    async checkProviderConfiguration() {
        try {
            const providerStatus = await apiClient.checkProviderConfiguration();
            
            // Show warning if no providers are configured
            showProviderWarning(providerStatus);
            
            // Update UI based on provider status
            updateUIForProviderStatus(providerStatus);
            
            // Store status globally for other components to use
            window.providerStatus = providerStatus;
            
            console.log('Provider status:', providerStatus);
            return providerStatus;
        } catch (error) {
            console.warn('Could not check provider configuration:', error);
            
            // Assume degraded state if we can't check
            const degradedStatus = {
                openrouter: false,
                openai: false,
                hasAnyProvider: false
            };
            
            showProviderWarning(degradedStatus);
            updateUIForProviderStatus(degradedStatus);
            window.providerStatus = degradedStatus;
            return degradedStatus;
        }
    }

    /**
     * Set up periodic health checks for API and providers
     */
    setupHealthChecks() {
        // Check API health every 30 seconds
        setInterval(async () => {
            const isHealthy = await apiClient.checkApiHealth();
            
            // Update global API health status
            window.apiHealthy = isHealthy;
            
            // If API is healthy, also check provider status every 5 minutes
            if (isHealthy) {
                const now = Date.now();
                const lastProviderCheck = window.lastProviderCheck || 0;
                
                if (now - lastProviderCheck > 300000) { // 5 minutes
                    await this.checkProviderConfiguration();
                    window.lastProviderCheck = now;
                }
            }
        }, 30000);
    }
}

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showNotification('An unexpected error occurred', 'error');
});

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.app = new App();
        window.app.init();
    });
} else {
    // DOM already loaded
    window.app = new App();
    window.app.init();
}

// Export for debugging and extensions
export default App;
//# sourceMappingURL=app.js.map
