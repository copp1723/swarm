// @ts-check
// Main Application Entry Point - Refactored for Unified Workspace
import { UnifiedWorkspace } from './components/workspace/unified-workspace.js';
import { WebSocketService } from './services/websocket.js';
import { StorageService } from './services/storage.js';
import { showNotification } from './utils/dom-helpers.js';
import { initApiKeySetup, showProviderWarning, updateUIForProviderStatus } from './components/api-key-setup.js';
import { apiClient } from './services/api-client.js';
import { darkModeManager } from './utils/dark-mode.js';

/**
 * Main Application class that manages the overall UI state and initialization
 * Supports both unified workspace and legacy interface modes
 */
class App {
    constructor() {
        /** @type {WebSocketService} WebSocket service instance */
        this.wsService = new WebSocketService();
        /** @type {StorageService} Storage service instance */
        this.storage = new StorageService();
        /** @type {UnifiedWorkspace|null} Unified workspace instance */
        this.workspace = null;
        
        // Keep legacy components for backward compatibility during transition
        /** @type {any|null} Legacy agent manager */
        this.agentManager = null;
        /** @type {any|null} Legacy collaboration modal */
        this.collaborationModal = null;
    }

    /**
     * Initialize the application with proper error handling and setup
     * Determines interface mode and initializes accordingly
     * @returns {Promise<void>}
     */
    async init() {
        try {
            // Initialize API key setup if needed
            initApiKeySetup();
            
            // Check provider configuration and update UI accordingly
            await this.checkProviderConfiguration();
            
            // Initialize WebSocket
            this.wsService.connect();
            
            // Check if we should use the new workspace
            const useUnifiedWorkspace = this.shouldUseUnifiedWorkspace();
            
            if (useUnifiedWorkspace) {
                await this.initUnifiedWorkspace();
            } else {
                await this.initLegacyInterface();
            }
            
            // Setup global event listeners
            this.setupGlobalListeners();
            
            // Load preferences
            this.loadGlobalPreferences();
            
            // Set up periodic health checks
            this.setupHealthChecks();
            
            // Show welcome notification
            const interfaceType = useUnifiedWorkspace ? 'Unified Workspace' : 'Classic Interface';
            showNotification(`MCP Agent ${interfaceType} loaded successfully`, 'success');
            
        } catch (error) {
            console.error('Failed to initialize app:', error);
            showNotification('Failed to initialize application', 'error');
        }
    }

    shouldUseUnifiedWorkspace() {
        // Check URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('workspace') === 'unified') {
            return true;
        }
        
        // Check localStorage preference
        const preference = localStorage.getItem('mcp_interface_preference');
        if (preference === 'unified') {
            return true;
        }
        
        // Default to unified workspace for new experience
        return true;
    }

    async initUnifiedWorkspace() {
        // Hide legacy UI elements
        const legacyElements = ['sidebar', 'agent-chats-container', 'open-collab-btn'];
        legacyElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) element.style.display = 'none';
        });
        
        // Create and initialize unified workspace
        this.workspace = new UnifiedWorkspace(this.agentManager, this.wsService, apiClient);
        this.workspace.init();
        
        // Add interface switcher
        this.addInterfaceSwitcher();
    }

    async initLegacyInterface() {
        // Dynamically import legacy components only if needed
        const { AgentManager } = await import('./agents/agent-manager.js');
        const { CollaborationModal } = await import('./components/collaboration-modal.js');
        const { WorkflowVisualization } = await import('./components/workflow-visualization.js');
        const { AgentStatusManager } = await import('./components/agent-status-manager.js');
        
        this.agentManager = new AgentManager();
        this.collaborationModal = new CollaborationModal(this.agentManager, this.wsService);
        this.workflowVisualization = new WorkflowVisualization();
        this.agentStatusManager = new AgentStatusManager(this.wsService);
        
        // Initialize legacy components
        await this.agentManager.init();
        await this.collaborationModal.init();
        this.agentStatusManager.init();
        
        // Setup legacy WebSocket listeners
        this.setupLegacyWebSocketListeners();
        
        // Add interface switcher
        this.addInterfaceSwitcher();
    }

    addInterfaceSwitcher() {
        const header = document.querySelector('header');
        if (!header) return;
        
        const switcherHtml = `
            <div class="interface-switcher" style="position: fixed; bottom: 20px; right: 20px; z-index: 1000;">
                <button id="switch-interface" class="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2">
                    <i data-lucide="toggle-left" class="w-4 h-4"></i>
                    <span>${this.workspace ? 'Switch to Classic' : 'Switch to Unified'}</span>
                </button>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', switcherHtml);
        
        document.getElementById('switch-interface').addEventListener('click', () => {
            const newPreference = this.workspace ? 'classic' : 'unified';
            localStorage.setItem('mcp_interface_preference', newPreference);
            window.location.reload();
        });
        
        // Update icons
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    setupLegacyWebSocketListeners() {
        // Listen for agent communication events to update status
        this.wsService.on('agent_communication', (data) => {
            const agentId = data.from_agent || data.communication?.from_agent;
            if (agentId && this.agentStatusManager) {
                this.agentStatusManager.updateAgentStatus(agentId, 'working', 'Communicating...');
            }
        });
        
        // Listen for task progress events
        this.wsService.on('task_progress', (data) => {
            // Update individual agent statuses if provided
            if (data.agent_statuses && this.agentStatusManager) {
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
            if (this.agentStatusManager) {
                const allStatuses = this.agentStatusManager.getAllAgentStatuses();
                Object.keys(allStatuses).forEach(agentId => {
                    if (allStatuses[agentId].status === 'working') {
                        this.agentStatusManager.updateAgentStatus(agentId, 'completed', 'Task completed');
                    }
                });
            }
        });
        
        // Listen for task errors
        this.wsService.on('task_error', (data) => {
            // Mark relevant agents as error state
            showNotification('Task error occurred', 'error');
        });
    }

    setupGlobalListeners() {
        // Global enhance prompt toggle (works for both interfaces)
        const enhanceToggle = document.getElementById('enhance-prompt-global') || document.getElementById('enhance-prompt');
        if (enhanceToggle) {
            enhanceToggle.addEventListener('change', (e) => {
                this.storage.setEnhancePromptSetting(e.target.checked);
            });
        }
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Cmd/Ctrl + K to focus on input
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                
                if (this.workspace) {
                    // Focus unified workspace input
                    const input = document.getElementById('command-input');
                    if (input) input.focus();
                } else if (this.agentManager) {
                    // Focus legacy agent input
                    const currentAgent = this.agentManager.currentAgentId;
                    if (currentAgent) {
                        const input = document.getElementById(`input-${currentAgent}`);
                        if (input) input.focus();
                    }
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
        const enhanceToggle = document.getElementById('enhance-prompt-global') || document.getElementById('enhance-prompt');
        if (enhanceToggle) {
            enhanceToggle.checked = this.storage.getEnhancePromptSetting();
        }
    }

    handleResize() {
        // Handle responsive behavior
        if (window.innerWidth < 768) {
            // Mobile view adjustments
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

    getWorkspace() {
        return this.workspace;
    }

    /**
     * Check and handle provider configuration status
     */
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
