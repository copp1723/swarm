/**
 * Agent UI Enhancements
 * Integrates new agent capabilities and features into the existing UI
 */

class AgentUIEnhancements {
    constructor() {
        this.agentProfiles = {
            product_01: {
                name: "Product Agent",
                role: "PLANNER",
                icon: "package",
                color: "#8B5CF6",
                description: "Product management, user stories, roadmaps, and PRDs",
                capabilities: ["product planning", "user story creation", "roadmap development", "filesystem access", "memory"]
            },
            coder_01: {
                name: "Coding Agent",
                role: "DEVELOPER", 
                icon: "code",
                color: "#3B82F6",
                description: "Code writing, refactoring, debugging, and optimization",
                capabilities: ["coding", "debugging", "refactoring", "code review", "filesystem access", "memory"]
            },
            bug_01: {
                name: "Bug Agent",
                role: "INCIDENT",
                icon: "alert-circle",
                color: "#EF4444",
                description: "Incident management, error analysis, and RCA documents",
                capabilities: ["incident management", "error analysis", "root cause analysis", "monitoring", "memory"]
            },
            tester_01: {
                name: "QA Engineer",
                role: "TESTER",
                icon: "check-circle",
                color: "#10B981",
                description: "Testing, bug identification, and test planning",
                capabilities: ["testing", "bug identification", "test planning", "filesystem access", "memory"]
            },
            devops_01: {
                name: "DevOps Engineer",
                role: "DEVOPS",
                icon: "server",
                color: "#F59E0B",
                description: "Infrastructure, deployment, and CI/CD",
                capabilities: ["deployment", "CI/CD", "infrastructure", "monitoring", "filesystem access"]
            },
            general_01: {
                name: "General Assistant",
                role: "GENERAL",
                icon: "help-circle",
                color: "#6B7280",
                description: "Versatile assistant for any task",
                capabilities: ["general assistance", "filesystem access", "memory"]
            },
            email_01: {
                name: "Email Agent",
                role: "EMAIL",
                icon: "mail",
                color: "#EC4899",
                description: "Email communication and webhook processing",
                capabilities: ["email ingestion", "webhook processing", "approval workflows", "notification management"]
            }
        };

        this.systemStatus = {
            database: true,
            redis: true,
            websocket: true,
            mcp_server: true
        };

        this.init();
    }

    init() {
        this.updateAgentProfiles();
        this.addSystemStatusBar();
        this.enhanceAgentCards();
        this.addWorkflowTemplates();
        this.setupAgentCommunication();
        this.addMemoryViewer();
        this.startStatusMonitoring();
    }

    updateAgentProfiles() {
        // Update agent window titles and descriptions
        Object.entries(this.agentProfiles).forEach(([agentId, profile]) => {
            const agentWindow = document.querySelector(`#agent-window-${agentId}`);
            if (agentWindow) {
                // Update title
                const titleElement = agentWindow.querySelector('.agent-title');
                if (titleElement) {
                    titleElement.innerHTML = `
                        <i data-lucide="${profile.icon}" style="color: ${profile.color};"></i>
                        ${profile.name}
                        <span class="agent-role-badge" style="background: ${profile.color}20; color: ${profile.color};">
                            ${profile.role}
                        </span>
                    `;
                }

                // Add description
                const headerElement = agentWindow.querySelector('.agent-header');
                if (headerElement && !headerElement.querySelector('.agent-description')) {
                    const descDiv = document.createElement('div');
                    descDiv.className = 'agent-description';
                    descDiv.textContent = profile.description;
                    descDiv.style.cssText = 'font-size: 12px; color: #6b7280; margin-top: 4px;';
                    headerElement.appendChild(descDiv);
                }

                // Add capability badges
                this.addCapabilityBadges(agentWindow, profile);
            }
        });
    }

    addCapabilityBadges(agentWindow, profile) {
        const headerElement = agentWindow.querySelector('.agent-header');
        if (!headerElement || headerElement.querySelector('.agent-capabilities')) return;

        const capabilitiesDiv = document.createElement('div');
        capabilitiesDiv.className = 'agent-capabilities';
        capabilitiesDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px;';

        const capabilityIcons = {
            'filesystem access': 'folder',
            'memory': 'brain',
            'coding': 'terminal',
            'debugging': 'bug',
            'monitoring': 'activity',
            'email ingestion': 'mail',
            'webhook processing': 'webhook'
        };

        profile.capabilities.forEach(capability => {
            const badge = document.createElement('span');
            badge.className = 'capability-badge';
            badge.title = capability;
            badge.style.cssText = `
                display: inline-flex;
                align-items: center;
                padding: 2px 8px;
                background: #f3f4f6;
                border-radius: 4px;
                font-size: 11px;
                gap: 4px;
                cursor: help;
                transition: all 0.2s ease;
            `;
            
            const icon = capabilityIcons[capability] || 'circle';
            badge.innerHTML = `<i data-lucide="${icon}" style="width: 12px; height: 12px;"></i>`;
            
            badge.addEventListener('mouseenter', () => {
                badge.style.background = profile.color + '20';
                badge.style.transform = 'translateY(-1px)';
            });
            
            badge.addEventListener('mouseleave', () => {
                badge.style.background = '#f3f4f6';
                badge.style.transform = '';
            });
            
            capabilitiesDiv.appendChild(badge);
        });

        headerElement.appendChild(capabilitiesDiv);
        if (window.lucide) lucide.createIcons();
    }

    addSystemStatusBar() {
        if (document.querySelector('.system-status-bar')) return;

        const statusBar = document.createElement('div');
        statusBar.className = 'system-status-bar';
        statusBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 40px;
            background: white;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            z-index: 1000;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        `;

        statusBar.innerHTML = `
            <div class="system-title" style="font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <i data-lucide="cpu" style="width: 16px; height: 16px;"></i>
                Multi-Agent System
            </div>
            <div class="system-status" style="display: flex; gap: 20px;">
                ${Object.entries(this.systemStatus).map(([service, status]) => `
                    <div class="status-item" data-service="${service}" style="display: flex; align-items: center; gap: 6px; font-size: 13px;">
                        <span class="status-dot ${status ? 'active' : 'error'}" style="
                            width: 6px;
                            height: 6px;
                            border-radius: 50%;
                            background: ${status ? '#10b981' : '#ef4444'};
                            ${status ? 'animation: pulse 2s infinite;' : ''}
                        "></span>
                        <span style="color: #6b7280;">${service.replace('_', ' ').toUpperCase()}</span>
                    </div>
                `).join('')}
            </div>
        `;

        document.body.insertBefore(statusBar, document.body.firstChild);
        document.body.style.paddingTop = '40px';
        
        // Add pulse animation
        const style = document.createElement('style');
        style.textContent = `
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
                70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
                100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
            }
        `;
        document.head.appendChild(style);
        
        if (window.lucide) lucide.createIcons();
    }

    enhanceAgentCards() {
        // Add status indicators to agent windows
        document.querySelectorAll('.agent-window').forEach(window => {
            const header = window.querySelector('.agent-header');
            if (header && !header.querySelector('.agent-status-indicator')) {
                const indicator = document.createElement('div');
                indicator.className = 'agent-status-indicator';
                indicator.style.cssText = `
                    position: absolute;
                    top: 10px;
                    right: 10px;
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: #10b981;
                    animation: pulse 2s infinite;
                `;
                header.style.position = 'relative';
                header.appendChild(indicator);
            }
        });
    }

    addWorkflowTemplates() {
        const collaborationHub = document.querySelector('#collaboration-hub');
        if (!collaborationHub || collaborationHub.querySelector('.workflow-templates')) return;

        const templatesSection = document.createElement('div');
        templatesSection.className = 'workflow-templates';
        templatesSection.style.cssText = 'margin-bottom: 20px;';
        
        templatesSection.innerHTML = `
            <h4 style="margin-bottom: 10px; font-weight: 600;">Quick Templates</h4>
            <div class="template-buttons" style="display: flex; flex-wrap: wrap; gap: 8px;">
                <button class="template-btn" data-template="code_review" style="
                    padding: 6px 12px;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    background: white;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                ">
                    <i data-lucide="git-pull-request" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i>
                    Code Review
                </button>
                <button class="template-btn" data-template="feature_dev" style="
                    padding: 6px 12px;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    background: white;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                ">
                    <i data-lucide="package-plus" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i>
                    Feature Development
                </button>
                <button class="template-btn" data-template="incident" style="
                    padding: 6px 12px;
                    border: 1px solid #e5e7eb;
                    border-radius: 6px;
                    background: white;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                ">
                    <i data-lucide="alert-triangle" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i>
                    Incident Response
                </button>
            </div>
        `;

        const taskInput = collaborationHub.querySelector('#collab-task');
        if (taskInput) {
            taskInput.parentElement.insertBefore(templatesSection, taskInput);
        }

        // Add hover effects
        templatesSection.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                btn.style.background = '#f3f4f6';
                btn.style.borderColor = '#3b82f6';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.background = 'white';
                btn.style.borderColor = '#e5e7eb';
            });
            btn.addEventListener('click', () => this.loadWorkflowTemplate(btn.dataset.template));
        });

        if (window.lucide) lucide.createIcons();
    }

    loadWorkflowTemplate(templateId) {
        const templates = {
            code_review: {
                task: "Review the codebase for quality, security, and best practices",
                agents: ['product_01', 'coder_01', 'tester_01', 'bug_01']
            },
            feature_dev: {
                task: "Develop a new feature with full testing and deployment",
                agents: ['product_01', 'coder_01', 'tester_01', 'bug_01', 'devops_01']
            },
            incident: {
                task: "Investigate and resolve production incident",
                agents: ['bug_01', 'coder_01', 'tester_01', 'devops_01']
            }
        };

        const template = templates[templateId];
        if (!template) return;

        // Set task description
        const taskInput = document.querySelector('#collab-task');
        if (taskInput) {
            taskInput.value = template.task;
        }

        // Select agents
        document.querySelectorAll('#collaboration-hub input[type="checkbox"]').forEach(cb => {
            cb.checked = template.agents.includes(cb.value);
        });

        // Show notification
        this.showNotification(`Loaded "${templateId.replace('_', ' ')}" template`);
    }

    setupAgentCommunication() {
        // Listen for agent messages in WebSocket
        if (window.socket) {
            window.socket.on('agent_communication', (data) => {
                this.displayAgentCommunication(data);
            });
        }
    }

    displayAgentCommunication(message) {
        const collabMessages = document.querySelector('#collab-messages');
        if (!collabMessages) return;

        const commDiv = document.createElement('div');
        commDiv.className = 'agent-communication-message';
        commDiv.style.cssText = `
            margin: 12px 0;
            padding: 12px;
            background: linear-gradient(135deg, #E0E7FF, #DBEAFE);
            border-radius: 8px;
            border-left: 3px solid #3b82f6;
            animation: slideIn 0.3s ease;
        `;

        commDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px;">
                <strong style="color: ${this.agentProfiles[message.from_agent]?.color || '#333'};">
                    ${this.agentProfiles[message.from_agent]?.name || message.from_agent}
                </strong>
                <span style="color: #3b82f6;">→</span>
                <strong style="color: ${this.agentProfiles[message.to_agent]?.color || '#333'};">
                    ${this.agentProfiles[message.to_agent]?.name || message.to_agent}
                </strong>
                <span style="margin-left: auto; color: #6b7280; font-size: 11px;">
                    ${new Date(message.timestamp).toLocaleTimeString()}
                </span>
            </div>
            <div style="color: #374151;">${message.message}</div>
            ${message.response ? `
                <div style="margin-top: 8px; padding: 8px; background: rgba(255,255,255,0.5); border-radius: 4px;">
                    <div style="font-size: 11px; font-weight: 600; color: #10b981; margin-bottom: 4px;">RESPONSE</div>
                    <div style="color: #374151;">${message.response}</div>
                </div>
            ` : ''}
        `;

        collabMessages.appendChild(commDiv);
        collabMessages.scrollTop = collabMessages.scrollHeight;

        // Add slide-in animation
        if (!document.querySelector('#agent-comm-styles')) {
            const style = document.createElement('style');
            style.id = 'agent-comm-styles';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateX(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    addMemoryViewer() {
        // Add memory button to each agent
        document.querySelectorAll('.agent-window').forEach(window => {
            const agentId = window.id.replace('agent-window-', '');
            const profile = this.agentProfiles[agentId];
            
            if (profile && profile.capabilities.includes('memory')) {
                const controls = window.querySelector('.agent-controls');
                if (controls && !controls.querySelector('.memory-btn')) {
                    const memoryBtn = document.createElement('button');
                    memoryBtn.className = 'memory-btn';
                    memoryBtn.innerHTML = '<i data-lucide="brain"></i>';
                    memoryBtn.title = 'View agent memory';
                    memoryBtn.style.cssText = `
                        padding: 6px;
                        border: 1px solid #e5e7eb;
                        border-radius: 4px;
                        background: white;
                        cursor: pointer;
                        transition: all 0.2s ease;
                    `;
                    
                    memoryBtn.addEventListener('click', () => this.toggleMemoryViewer(agentId));
                    controls.appendChild(memoryBtn);
                }
            }
        });

        if (window.lucide) lucide.createIcons();
    }

    toggleMemoryViewer(agentId) {
        const window = document.querySelector(`#agent-window-${agentId}`);
        let memoryPanel = window.querySelector('.memory-panel');
        
        if (memoryPanel) {
            memoryPanel.style.display = memoryPanel.style.display === 'none' ? 'block' : 'none';
        } else {
            memoryPanel = document.createElement('div');
            memoryPanel.className = 'memory-panel';
            memoryPanel.style.cssText = `
                background: #f9fafb;
                border-top: 1px solid #e5e7eb;
                padding: 16px;
                max-height: 200px;
                overflow-y: auto;
            `;
            
            memoryPanel.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <i data-lucide="brain" style="width: 16px; height: 16px;"></i>
                    <strong>Agent Memory</strong>
                    <span style="margin-left: auto; font-size: 12px; color: #6b7280;">Loading...</span>
                </div>
                <div class="memory-list"></div>
            `;
            
            window.appendChild(memoryPanel);
            if (window.lucide) lucide.createIcons();
            
            // Load memory data
            this.loadAgentMemory(agentId);
        }
    }

    async loadAgentMemory(agentId) {
        try {
            const response = await fetch(`/api/memory/${agentId}`);
            const memories = await response.json();
            
            const memoryPanel = document.querySelector(`#agent-window-${agentId} .memory-panel`);
            const memoryList = memoryPanel.querySelector('.memory-list');
            const statusSpan = memoryPanel.querySelector('span');
            
            statusSpan.textContent = `${memories.length} memories`;
            
            if (memories.length === 0) {
                memoryList.innerHTML = '<div style="color: #6b7280; font-size: 14px;">No memories yet</div>';
            } else {
                memoryList.innerHTML = memories.map(memory => `
                    <div style="padding: 8px; margin-bottom: 8px; background: white; border-radius: 4px; border: 1px solid #e5e7eb;">
                        <div style="font-size: 14px; margin-bottom: 4px;">${memory.content}</div>
                        <div style="display: flex; gap: 12px; font-size: 11px; color: #6b7280;">
                            <span>${new Date(memory.created).toLocaleDateString()}</span>
                            <span style="color: #10b981;">${memory.relevance_score || 85}% relevant</span>
                        </div>
                    </div>
                `).join('');
            }
        } catch (error) {
            console.error('Failed to load agent memory:', error);
        }
    }

    startStatusMonitoring() {
        // Poll health endpoint every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/health');
                const health = await response.json();
                
                // Update status indicators
                Object.entries(health).forEach(([service, status]) => {
                    const item = document.querySelector(`.status-item[data-service="${service}"]`);
                    if (item) {
                        const dot = item.querySelector('.status-dot');
                        if (status.status === 'healthy') {
                            dot.classList.add('active');
                            dot.classList.remove('error');
                        } else {
                            dot.classList.add('error');
                            dot.classList.remove('active');
                        }
                    }
                });
            } catch (error) {
                console.error('Health check failed:', error);
            }
        }, 30000);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = 'ui-notification';
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1001;
            animation: slideUp 0.3s ease;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideDown 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
        
        // Add animation
        if (!document.querySelector('#notification-styles')) {
            const style = document.createElement('style');
            style.id = 'notification-styles';
            style.textContent = `
                @keyframes slideUp {
                    from { transform: translateY(100px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
                @keyframes slideDown {
                    from { transform: translateY(0); opacity: 1; }
                    to { transform: translateY(100px); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// Initialize enhancements when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.agentUIEnhancements = new AgentUIEnhancements();
    });
} else {
    window.agentUIEnhancements = new AgentUIEnhancements();
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentUIEnhancements;
}