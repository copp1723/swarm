/**
 * Drag and Drop utilities for agent workspace
 */

class DragDropManager {
    constructor() {
        this.draggedElement = null;
        this.dropZones = new Set();
        this.init();
    }

    init() {
        this.setupGlobalEventListeners();
    }

    setupGlobalEventListeners() {
        document.addEventListener('dragover', (e) => {
            e.preventDefault(); // Allow drop
        });

        document.addEventListener('drop', (e) => {
            e.preventDefault();
            this.handleGlobalDrop(e);
        });
    }

    /**
     * Make an element draggable
     * @param {HTMLElement} element 
     * @param {Object} data - Data to carry with drag
     */
    makeDraggable(element, data = {}) {
        element.draggable = true;
        element.classList.add('draggable');
        
        element.addEventListener('dragstart', (e) => {
            this.draggedElement = element;
            element.classList.add('dragging');
            
            // Store data
            e.dataTransfer.setData('text/plain', JSON.stringify(data));
            e.dataTransfer.effectAllowed = 'move';
            
            // Create drag image
            const dragImage = this.createDragImage(element, data);
            if (dragImage) {
                e.dataTransfer.setDragImage(dragImage, 0, 0);
            }
        });

        element.addEventListener('dragend', (e) => {
            element.classList.remove('dragging');
            this.draggedElement = null;
            this.cleanup();
        });
    }

    /**
     * Register a drop zone
     * @param {HTMLElement} element 
     * @param {Function} onDrop - Callback when item is dropped
     * @param {Function} onDragOver - Optional callback for drag over
     */
    registerDropZone(element, onDrop, onDragOver = null) {
        this.dropZones.add(element);
        element.classList.add('drop-zone');
        
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            element.classList.add('drag-over');
            
            if (onDragOver) {
                onDragOver(e, this.draggedElement);
            }
        });

        element.addEventListener('dragleave', (e) => {
            // Only remove class if we're leaving the drop zone itself
            if (!element.contains(e.relatedTarget)) {
                element.classList.remove('drag-over');
            }
        });

        element.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            element.classList.remove('drag-over');
            
            try {
                const data = JSON.parse(e.dataTransfer.getData('text/plain'));
                onDrop(e, data, this.draggedElement);
            } catch (error) {
                console.error('Error parsing drop data:', error);
            }
        });
    }

    /**
     * Create a custom drag image
     * @param {HTMLElement} element 
     * @param {Object} data 
     */
    createDragImage(element, data) {
        if (data.type === 'agent') {
            const dragImage = document.createElement('div');
            dragImage.style.cssText = `
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                position: absolute;
                top: -1000px;
                left: -1000px;
                z-index: 9999;
                pointer-events: none;
                white-space: nowrap;
            `;
            dragImage.textContent = `📄 ${data.name || data.agent_id}`;
            
            document.body.appendChild(dragImage);
            
            // Clean up after drag
            setTimeout(() => {
                if (document.body.contains(dragImage)) {
                    document.body.removeChild(dragImage);
                }
            }, 100);
            
            return dragImage;
        }
        return null;
    }

    /**
     * Handle global drop events
     * @param {DragEvent} e 
     */
    handleGlobalDrop(e) {
        // Remove visual indicators
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    /**
     * Cleanup drag state
     */
    cleanup() {
        document.querySelectorAll('.dragging').forEach(el => {
            el.classList.remove('dragging');
        });
        document.querySelectorAll('.drag-over').forEach(el => {
            el.classList.remove('drag-over');
        });
    }

    /**
     * Enable agent dragging for workspace
     * @param {string} agentId 
     * @param {HTMLElement} agentElement 
     */
    enableAgentDragging(agentId, agentElement) {
        this.makeDraggable(agentElement, {
            type: 'agent',
            agent_id: agentId,
            name: agentElement.querySelector('.agent-name')?.textContent || agentId
        });
    }

    /**
     * Setup workspace drop zones
     * @param {HTMLElement} workspaceContainer 
     */
    setupWorkspaceDropZones(workspaceContainer) {
        // Main workspace area
        this.registerDropZone(workspaceContainer, (e, data, element) => {
            if (data.type === 'agent') {
                this.handleAgentDrop(data, e);
            }
        });

        // Chat areas
        const chatContainers = workspaceContainer.querySelectorAll('[id^="chat-"]');
        chatContainers.forEach(container => {
            this.registerDropZone(container, (e, data) => {
                if (data.type === 'agent') {
                    const targetAgentId = container.id.replace('chat-', '');
                    this.handleAgentToChatDrop(data.agent_id, targetAgentId);
                }
            });
        });
    }

    /**
     * Handle agent drop in workspace
     * @param {Object} agentData 
     * @param {DragEvent} event 
     */
    handleAgentDrop(agentData, event) {
        console.log('Agent dropped in workspace:', agentData);
        
        // Get drop coordinates
        const rect = event.currentTarget.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // Emit custom event for other components to handle
        const dropEvent = new CustomEvent('agentDropped', {
            detail: {
                agent_id: agentData.agent_id,
                position: { x, y },
                name: agentData.name
            }
        });
        
        document.dispatchEvent(dropEvent);
        
        // Show visual feedback
        this.showDropFeedback(agentData, event.currentTarget, { x, y });
    }

    /**
     * Handle agent dropped onto another agent's chat
     * @param {string} sourceAgentId 
     * @param {string} targetAgentId 
     */
    handleAgentToChatDrop(sourceAgentId, targetAgentId) {
        console.log(`Agent ${sourceAgentId} dropped onto ${targetAgentId}'s chat`);
        
        // Emit collaboration event
        const collabEvent = new CustomEvent('agentCollaboration', {
            detail: {
                source: sourceAgentId,
                target: targetAgentId,
                type: 'chat_handoff'
            }
        });
        
        document.dispatchEvent(collabEvent);
    }

    /**
     * Show visual feedback for drop
     * @param {Object} agentData 
     * @param {HTMLElement} container 
     * @param {Object} position 
     */
    showDropFeedback(agentData, container, position) {
        const feedback = document.createElement('div');
        feedback.style.cssText = `
            position: absolute;
            left: ${position.x}px;
            top: ${position.y}px;
            background: rgba(102, 126, 234, 0.1);
            border: 2px dashed #667eea;
            border-radius: 8px;
            padding: 16px;
            pointer-events: none;
            transform: translate(-50%, -50%);
            z-index: 1000;
            animation: dropFeedback 0.6s ease-out forwards;
        `;
        feedback.innerHTML = `
            <div style="text-align: center; color: #667eea; font-weight: 500;">
                <div style="font-size: 24px; margin-bottom: 4px;">📄</div>
                <div>${agentData.name} added to workspace</div>
            </div>
        `;
        
        container.appendChild(feedback);
        
        // Add animation keyframes if not exists
        if (!document.querySelector('#drop-feedback-styles')) {
            const style = document.createElement('style');
            style.id = 'drop-feedback-styles';
            style.textContent = `
                @keyframes dropFeedback {
                    0% { opacity: 1; transform: translate(-50%, -50%) scale(0.8); }
                    50% { opacity: 1; transform: translate(-50%, -50%) scale(1.1); }
                    100% { opacity: 0; transform: translate(-50%, -50%) scale(1); }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Remove after animation
        setTimeout(() => {
            if (container.contains(feedback)) {
                container.removeChild(feedback);
            }
        }, 600);
    }
}

// Export singleton instance
export const dragDropManager = new DragDropManager();
export default dragDropManager;

