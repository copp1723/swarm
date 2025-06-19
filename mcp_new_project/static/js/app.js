// Main Application Entry Point
import { AgentManager } from './agents/agent-manager.js';
import { CollaborationModal } from './components/collaboration-modal.js';
import { WorkflowVisualization } from './components/workflow-visualization.js';
import { AgentStatusManager } from './components/agent-status-manager.js';
import { WebSocketService } from './services/websocket.js';
import { StorageService } from './services/storage.js';
import { showNotification } from './utils/dom-helpers.js';
import { initApiKeySetup } from './components/api-key-setup.js';

class App {
    constructor() {
        this.agentManager = new AgentManager();
        this.wsService = new WebSocketService();
        this.storage = new StorageService();
        this.collaborationModal = null;
        this.workflowVisualization = new WorkflowVisualization();
        this.agentStatusManager = new AgentStatusManager();
    }

    async init() {
        try {
            // Initialize API key setup if needed
            initApiKeySetup();
            
            // Initialize core components
            await this.agentManager.init();
            
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