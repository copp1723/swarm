// Advanced Workflow Visualization Component
import { createElement, updateIcons } from '../utils/dom-helpers.js';
import { getAgentById, getAgentColor } from '../agents/agent-config.js';

export class WorkflowVisualization {
    constructor() {
        this.container = null;
        this.agents = [];
        this.connections = [];
        this.currentStep = 0;
        this.totalSteps = 0;
    }

    init(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error('WorkflowVisualization: Container not found');
            return false;
        }
        return true;
    }

    createWorkflowDiagram(agentIds, taskDescription) {
        if (!this.container) return;

        this.agents = agentIds.map(id => getAgentById(id)).filter(Boolean);
        this.totalSteps = this.agents.length;
        this.currentStep = 0;

        this.container.innerHTML = `
            <div class="workflow-visualization bg-white rounded-xl shadow-lg border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-lg font-semibold text-gray-900 flex items-center">
                        <i data-lucide="git-branch" class="w-5 h-5 mr-2 text-blue-600"></i>
                        Workflow Visualization
                    </h3>
                    <div class="flex items-center space-x-2 text-sm text-gray-600">
                        <span>Step</span>
                        <span id="current-step" class="font-medium text-blue-600">${this.currentStep}</span>
                        <span>of</span>
                        <span class="font-medium">${this.totalSteps}</span>
                    </div>
                </div>

                <!-- Task Description -->
                <div class="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center">
                        <i data-lucide="target" class="w-4 h-4 mr-2"></i>
                        Task Description
                    </h4>
                    <p class="text-sm text-gray-600">${taskDescription}</p>
                </div>

                <!-- Agent Flow Diagram -->
                <div id="agent-flow" class="relative">
                    ${this.createAgentFlow()}
                </div>

                <!-- Progress Timeline -->
                <div class="mt-6 border-t border-gray-200 pt-4">
                    <h4 class="text-sm font-medium text-gray-700 mb-3 flex items-center">
                        <i data-lucide="clock" class="w-4 h-4 mr-2"></i>
                        Execution Timeline
                    </h4>
                    <div id="workflow-timeline" class="space-y-2 max-h-32 overflow-y-auto">
                        <!-- Timeline events will be added here -->
                    </div>
                </div>
            </div>
        `;

        updateIcons();
        this.addTimelineEvent('Workflow initialized', 'system');
    }

    createAgentFlow() {
        if (this.agents.length === 0) return '';

        const agentNodes = this.agents.map((agent, index) => {
            const agentColor = getAgentColor(agent.color);
            const isFirst = index === 0;
            const isLast = index === this.agents.length - 1;
            
            return `
                <div class="agent-node relative" data-agent-id="${agent.id}" data-step="${index + 1}">
                    <!-- Connection line (if not first) -->
                    ${!isFirst ? `
                        <div class="connection-line absolute -left-12 top-1/2 w-12 h-0.5 bg-gray-300 transform -translate-y-1/2">
                            <div class="connection-progress h-full bg-blue-500 transition-all duration-500" style="width: 0%"></div>
                        </div>
                    ` : ''}
                    
                    <!-- Agent Card -->
                    <div class="agent-card bg-white border-2 border-gray-200 rounded-xl p-4 w-48 transition-all duration-300">
                        <div class="flex items-center space-x-3 mb-3">
                            <div class="agent-avatar w-10 h-10 ${agentColor} rounded-lg flex items-center justify-center relative">
                                <i data-lucide="${agent.icon}" class="w-5 h-5 text-white"></i>
                                <div class="status-indicator absolute -top-1 -right-1 w-3 h-3 rounded-full bg-gray-300 border-2 border-white"></div>
                            </div>
                            <div class="flex-1">
                                <div class="font-medium text-gray-900 text-sm">${agent.name}</div>
                                <div class="text-xs text-gray-500">${agent.role}</div>
                            </div>
                        </div>
                        
                        <!-- Agent Progress -->
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs">
                                <span class="text-gray-600">Progress</span>
                                <span class="agent-progress font-medium">0%</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-2">
                                <div class="agent-progress-bar ${agentColor.replace('bg-', 'bg-')} h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                            </div>
                        </div>
                        
                        <!-- Current Activity -->
                        <div class="mt-3 text-xs text-gray-600 agent-activity">
                            Waiting to start...
                        </div>
                    </div>
                    
                    <!-- Step Number -->
                    <div class="step-number absolute -top-3 left-1/2 transform -translate-x-1/2 w-6 h-6 bg-gray-300 text-white rounded-full flex items-center justify-center text-xs font-medium">
                        ${index + 1}
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="flex items-center justify-center space-x-12 overflow-x-auto pb-4">
                ${agentNodes}
            </div>
        `;
    }

    updateAgentStatus(agentId, status, progress = null, activity = null) {
        const agentNode = this.container.querySelector(`[data-agent-id="${agentId}"]`);
        if (!agentNode) return;

        const statusIndicator = agentNode.querySelector('.status-indicator');
        const agentCard = agentNode.querySelector('.agent-card');
        const progressText = agentNode.querySelector('.agent-progress');
        const progressBar = agentNode.querySelector('.agent-progress-bar');
        const activityText = agentNode.querySelector('.agent-activity');
        const stepNumber = agentNode.querySelector('.step-number');

        // Update status indicator
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-white';
            switch (status) {
                case 'waiting':
                    statusIndicator.classList.add('bg-gray-300');
                    break;
                case 'working':
                    statusIndicator.classList.add('bg-yellow-400', 'animate-pulse');
                    agentCard.classList.add('border-yellow-300', 'bg-yellow-50');
                    agentCard.classList.remove('border-gray-200');
                    break;
                case 'completed':
                    statusIndicator.classList.add('bg-green-400');
                    agentCard.classList.add('border-green-300', 'bg-green-50');
                    agentCard.classList.remove('border-gray-200', 'border-yellow-300', 'bg-yellow-50');
                    stepNumber.classList.add('bg-green-500');
                    stepNumber.classList.remove('bg-gray-300');
                    break;
                case 'error':
                    statusIndicator.classList.add('bg-red-400');
                    agentCard.classList.add('border-red-300', 'bg-red-50');
                    agentCard.classList.remove('border-gray-200', 'border-yellow-300', 'bg-yellow-50');
                    stepNumber.classList.add('bg-red-500');
                    stepNumber.classList.remove('bg-gray-300');
                    break;
            }
        }

        // Update progress
        if (progress !== null && progressText && progressBar) {
            progressText.textContent = `${progress}%`;
            progressBar.style.width = `${progress}%`;
        }

        // Update activity text
        if (activity && activityText) {
            activityText.textContent = activity;
        }

        // Update connection line to this agent
        const stepIndex = parseInt(agentNode.dataset.step) - 1;
        if (stepIndex > 0 && status === 'completed') {
            const connectionProgress = agentNode.querySelector('.connection-progress');
            if (connectionProgress) {
                connectionProgress.style.width = '100%';
            }
        }
    }

    updateCurrentStep(step) {
        this.currentStep = step;
        const currentStepElement = this.container.querySelector('#current-step');
        if (currentStepElement) {
            currentStepElement.textContent = step;
        }

        // Highlight current step
        this.container.querySelectorAll('.step-number').forEach((stepEl, index) => {
            if (index < step) {
                stepEl.classList.add('bg-blue-500');
                stepEl.classList.remove('bg-gray-300');
            } else if (index === step) {
                stepEl.classList.add('bg-blue-500', 'animate-pulse');
                stepEl.classList.remove('bg-gray-300');
            }
        });
    }

    addTimelineEvent(event, type = 'system', agentId = null) {
        const timeline = this.container.querySelector('#workflow-timeline');
        if (!timeline) return;

        const timestamp = new Date();
        const eventDiv = createElement('div', 'flex items-center space-x-2 text-xs timeline-event opacity-0 animate-fadeIn');
        
        let iconClass = 'w-3 h-3 text-gray-500';
        let textClass = 'text-gray-600';
        
        switch (type) {
            case 'agent':
                iconClass = 'w-3 h-3 text-blue-500';
                textClass = 'text-blue-700';
                break;
            case 'error':
                iconClass = 'w-3 h-3 text-red-500';
                textClass = 'text-red-700';
                break;
            case 'complete':
                iconClass = 'w-3 h-3 text-green-500';
                textClass = 'text-green-700';
                break;
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

        // Trigger animation
        setTimeout(() => {
            eventDiv.classList.remove('opacity-0');
            eventDiv.classList.add('opacity-100');
        }, 10);
    }

    reset() {
        this.currentStep = 0;
        this.agents = [];
        this.connections = [];
        if (this.container) {
            this.container.innerHTML = '';
        }
    }

    // Simulate workflow progression for demo purposes
    simulateProgress() {
        if (!this.agents.length) return;

        this.agents.forEach((agent, index) => {
            setTimeout(() => {
                this.updateAgentStatus(agent.id, 'working', 0, 'Processing...');
                this.updateCurrentStep(index + 1);
                this.addTimelineEvent(`${agent.name} started working`, 'agent', agent.id);

                // Simulate progress
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += Math.random() * 20;
                    if (progress >= 100) {
                        progress = 100;
                        this.updateAgentStatus(agent.id, 'completed', progress, 'Completed successfully');
                        this.addTimelineEvent(`${agent.name} completed task`, 'complete', agent.id);
                        clearInterval(progressInterval);
                    } else {
                        this.updateAgentStatus(agent.id, 'working', Math.round(progress), 'Processing...');
                    }
                }, 500);
            }, index * 2000);
        });
    }
}

// CSS for animations (to be added to main CSS file)
export const workflowVisualizationCSS = `
.workflow-visualization .timeline-event {
    transition: opacity 0.3s ease-in-out;
}

.workflow-visualization .animate-fadeIn {
    animation: fadeInTimeline 0.3s ease-in-out forwards;
}

@keyframes fadeInTimeline {
    from {
        opacity: 0;
        transform: translateY(-5px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.workflow-visualization .agent-card {
    transition: all 0.3s ease-in-out;
}

.workflow-visualization .connection-progress {
    transition: width 0.5s ease-in-out;
}

.workflow-visualization .step-number {
    transition: all 0.3s ease-in-out;
}
`;


//# sourceMappingURL=workflow-visualization.js.map
