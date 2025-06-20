/**
 * Virtual Chat Container Implementation
 * Provides virtual scrolling for chat messages to handle thousands of messages efficiently
 */

class VirtualChatContainer {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.messages = [];
        this.visibleMessages = [];
        
        // Configuration
        this.config = {
            itemHeight: options.itemHeight || 100, // Average message height
            overscan: options.overscan || 5, // Extra items to render outside viewport
            scrollThreshold: options.scrollThreshold || 50, // Auto-scroll threshold
            maxMessages: options.maxMessages || 10000, // Maximum messages to keep in memory
            ...options
        };
        
        // State
        this.scrollTop = 0;
        this.containerHeight = 0;
        this.totalHeight = 0;
        this.startIndex = 0;
        this.endIndex = 0;
        this.isAutoScrollEnabled = true;
        this.isScrolling = false;
        this.scrollToBottomQueued = false;
        
        // Performance optimization
        this.rafId = null;
        this.resizeObserver = null;
        this.heightCache = new Map();
        this.measuredHeights = new Map();
        
        this.init();
    }
    
    init() {
        this.createVirtualContainer();
        this.setupEventListeners();
        this.setupResizeObserver();
        this.updateVisibleRange();
    }
    
    createVirtualContainer() {
        // Clear existing content
        this.container.innerHTML = '';
        
        // Create virtual scrolling structure
        this.container.innerHTML = `
            <div class="virtual-chat-wrapper" style="height: 100%; overflow: auto; position: relative;">
                <div class="virtual-chat-spacer" style="height: 0px; width: 100%;"></div>
                <div class="virtual-chat-content" style="position: relative; transform: translateY(0px);">
                    <!-- Virtual messages will be rendered here -->
                </div>
                <div class="virtual-chat-bottom-spacer" style="height: 0px; width: 100%;"></div>
            </div>
            <div class="scroll-to-bottom-btn" style="
                position: absolute;
                bottom: 20px;
                right: 20px;
                background: #3b82f6;
                color: white;
                border-radius: 50%;
                width: 48px;
                height: 48px;
                display: none;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: all 0.2s ease;
                z-index: 10;
            " title="Scroll to bottom">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6,9 12,15 18,9"></polyline>
                </svg>
            </div>
        `;
        
        // Get references
        this.wrapper = this.container.querySelector('.virtual-chat-wrapper');
        this.spacer = this.container.querySelector('.virtual-chat-spacer');
        this.content = this.container.querySelector('.virtual-chat-content');
        this.bottomSpacer = this.container.querySelector('.virtual-chat-bottom-spacer');
        this.scrollButton = this.container.querySelector('.scroll-to-bottom-btn');
        
        // Update container height
        this.containerHeight = this.wrapper.clientHeight;
    }
    
    setupEventListeners() {
        // Scroll event with throttling
        this.wrapper.addEventListener('scroll', this.throttle(this.handleScroll.bind(this), 16));
        
        // Scroll to bottom button
        this.scrollButton.addEventListener('click', () => {
            this.scrollToBottom(true);
        });
        
        // Wheel event for scroll detection
        this.wrapper.addEventListener('wheel', (e) => {
            if (e.deltaY < 0) {
                // Scrolling up - disable auto-scroll
                this.isAutoScrollEnabled = false;
            }
        });
    }
    
    setupResizeObserver() {
        if ('ResizeObserver' in window) {
            this.resizeObserver = new ResizeObserver(entries => {
                for (let entry of entries) {
                    const newHeight = entry.contentRect.height;
                    if (newHeight !== this.containerHeight) {
                        this.containerHeight = newHeight;
                        this.updateVisibleRange();
                    }
                }
            });
            this.resizeObserver.observe(this.wrapper);
        }
    }
    
    handleScroll() {
        this.scrollTop = this.wrapper.scrollTop;
        
        // Check if user is near bottom
        const isNearBottom = this.scrollTop + this.containerHeight >= this.totalHeight - this.config.scrollThreshold;
        
        if (isNearBottom) {
            this.isAutoScrollEnabled = true;
            this.scrollButton.style.display = 'none';
        } else {
            this.scrollButton.style.display = 'flex';
        }
        
        // Update visible range
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
        }
        this.rafId = requestAnimationFrame(() => {
            this.updateVisibleRange();
        });
    }
    
    updateVisibleRange() {
        if (this.messages.length === 0) {
            this.renderMessages();
            return;
        }
        
        // Calculate visible range with overscan
        const scrollTop = this.scrollTop;
        const scrollBottom = scrollTop + this.containerHeight;
        
        // Find start index
        let startIndex = 0;
        let accumulatedHeight = 0;
        
        for (let i = 0; i < this.messages.length; i++) {
            const messageHeight = this.getMessageHeight(i);
            if (accumulatedHeight + messageHeight > scrollTop) {
                startIndex = Math.max(0, i - this.config.overscan);
                break;
            }
            accumulatedHeight += messageHeight;
        }
        
        // Find end index
        let endIndex = startIndex;
        accumulatedHeight = this.getOffsetTop(startIndex);
        
        for (let i = startIndex; i < this.messages.length; i++) {
            if (accumulatedHeight > scrollBottom) {
                endIndex = Math.min(this.messages.length - 1, i + this.config.overscan);
                break;
            }
            accumulatedHeight += this.getMessageHeight(i);
            endIndex = i;
        }
        
        // Update if range changed
        if (startIndex !== this.startIndex || endIndex !== this.endIndex) {
            this.startIndex = startIndex;
            this.endIndex = endIndex;
            this.renderMessages();
        }
    }
    
    getMessageHeight(index) {
        const messageId = this.messages[index]?.id;
        if (messageId && this.measuredHeights.has(messageId)) {
            return this.measuredHeights.get(messageId);
        }
        return this.config.itemHeight;
    }
    
    getOffsetTop(index) {
        let offset = 0;
        for (let i = 0; i < index; i++) {
            offset += this.getMessageHeight(i);
        }
        return offset;
    }
    
    measureMessage(element, messageId) {
        if (element && messageId) {
            const height = element.offsetHeight;
            this.measuredHeights.set(messageId, height);
            return height;
        }
        return this.config.itemHeight;
    }
    
    renderMessages() {
        if (!this.content) return;
        
        // Calculate total height
        this.totalHeight = 0;
        for (let i = 0; i < this.messages.length; i++) {
            this.totalHeight += this.getMessageHeight(i);
        }
        
        // Update spacers
        const offsetTop = this.getOffsetTop(this.startIndex);
        const offsetBottom = this.totalHeight - this.getOffsetTop(this.endIndex + 1);
        
        this.spacer.style.height = `${offsetTop}px`;
        this.bottomSpacer.style.height = `${offsetBottom}px`;
        
        // Render visible messages
        const fragment = document.createDocumentFragment();
        
        for (let i = this.startIndex; i <= this.endIndex; i++) {
            if (i < this.messages.length) {
                const messageEl = this.createMessageElement(this.messages[i], i);
                fragment.appendChild(messageEl);
            }
        }
        
        this.content.innerHTML = '';
        this.content.appendChild(fragment);
        
        // Measure rendered messages
        this.content.querySelectorAll('.virtual-message').forEach((el, index) => {
            const globalIndex = this.startIndex + index;
            const message = this.messages[globalIndex];
            if (message) {
                this.measureMessage(el, message.id);
            }
        });
        
        // Handle queued scroll to bottom
        if (this.scrollToBottomQueued) {
            this.scrollToBottomQueued = false;
            this.scrollToBottom(false);
        }
    }
    
    createMessageElement(message, index) {
        const messageEl = document.createElement('div');
        messageEl.className = `virtual-message chat-message ${message.type === 'user' ? 'user-message' : 'agent-message'}`;
        messageEl.dataset.messageId = message.id;
        messageEl.dataset.index = index;
        
        if (message.type === 'user') {
            messageEl.innerHTML = this.renderUserMessage(message);
        } else {
            messageEl.innerHTML = this.renderAgentMessage(message);
        }
        
        // Add animation class for new messages
        if (message.isNew) {
            messageEl.classList.add('animate-slide-in');
            // Remove the flag and animation class after animation
            setTimeout(() => {
                message.isNew = false;
                messageEl.classList.remove('animate-slide-in');
            }, 300);
        }
        
        return messageEl;
    }
    
    renderUserMessage(message) {
        return `
            <div class="flex justify-end mb-4">
                <div class="max-w-[80%] px-4 py-2 bg-blue-600 text-white rounded-lg rounded-br-none text-sm">
                    ${this.escapeHtml(message.content)}
                    ${message.timestamp ? `<div class="text-xs opacity-75 mt-1">${new Date(message.timestamp).toLocaleTimeString()}</div>` : ''}
                </div>
            </div>
        `;
    }
    
    renderAgentMessage(message) {
        return `
            <div class="flex justify-start mb-4">
                <div class="max-w-[80%]">
                    <div class="flex items-center space-x-2 mb-2">
                        <div class="font-medium text-xs text-gray-600">${this.escapeHtml(message.agentName || 'Assistant')}</div>
                        ${message.enhanced ? '<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">Enhanced</span>' : ''}
                        ${message.timestamp ? `<span class="text-xs text-gray-400">${new Date(message.timestamp).toLocaleTimeString()}</span>` : ''}
                    </div>
                    <div class="px-6 py-4 bg-gray-100 text-gray-800 rounded-lg rounded-bl-none shadow-sm">
                        <div class="agent-response text-sm leading-relaxed">
                            ${this.formatAgentResponse(message.content)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Message management methods
    addMessage(message) {
        // Generate ID if not provided
        if (!message.id) {
            message.id = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }
        
        // Add timestamp if not provided
        if (!message.timestamp) {
            message.timestamp = new Date().toISOString();
        }
        
        // Mark as new for animation
        message.isNew = true;
        
        // Add to messages array
        this.messages.push(message);
        
        // Trim messages if exceeding limit
        if (this.messages.length > this.config.maxMessages) {
            const removed = this.messages.splice(0, this.messages.length - this.config.maxMessages);
            // Clean up height cache for removed messages
            removed.forEach(msg => {
                this.measuredHeights.delete(msg.id);
            });
        }
        
        // Update visible range
        this.updateVisibleRange();
        
        // Auto-scroll to bottom if enabled
        if (this.isAutoScrollEnabled) {
            // Queue scroll to bottom after render
            this.scrollToBottomQueued = true;
        }
    }
    
    addMessages(messages) {
        messages.forEach(message => {
            this.addMessage(message);
        });
    }
    
    clearMessages() {
        this.messages = [];
        this.measuredHeights.clear();
        this.startIndex = 0;
        this.endIndex = 0;
        this.totalHeight = 0;
        this.isAutoScrollEnabled = true;
        this.renderMessages();
    }
    
    scrollToBottom(smooth = true) {
        if (!this.wrapper) return;
        
        const scrollOptions = {
            top: this.totalHeight,
            behavior: smooth ? 'smooth' : 'auto'
        };
        
        this.wrapper.scrollTo(scrollOptions);
        this.isAutoScrollEnabled = true;
        this.scrollButton.style.display = 'none';
    }
    
    scrollToMessage(messageId) {
        const messageIndex = this.messages.findIndex(msg => msg.id === messageId);
        if (messageIndex === -1) return;
        
        const offsetTop = this.getOffsetTop(messageIndex);
        this.wrapper.scrollTo({
            top: offsetTop,
            behavior: 'smooth'
        });
    }
    
    updateMessage(messageId, updates) {
        const messageIndex = this.messages.findIndex(msg => msg.id === messageId);
        if (messageIndex === -1) return;
        
        // Update message
        Object.assign(this.messages[messageIndex], updates);
        
        // Clear height cache for this message
        this.measuredHeights.delete(messageId);
        
        // Re-render if message is visible
        if (messageIndex >= this.startIndex && messageIndex <= this.endIndex) {
            this.renderMessages();
        }
    }
    
    removeMessage(messageId) {
        const messageIndex = this.messages.findIndex(msg => msg.id === messageId);
        if (messageIndex === -1) return;
        
        // Remove from messages array
        this.messages.splice(messageIndex, 1);
        
        // Clean up height cache
        this.measuredHeights.delete(messageId);
        
        // Update visible range
        this.updateVisibleRange();
    }
    
    // Utility methods
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatAgentResponse(text) {
        // Reuse the existing formatAgentResponse function from the main interface
        if (window.formatAgentResponse) {
            return window.formatAgentResponse(text);
        }
        
        // Fallback formatting
        return this.escapeHtml(text).replace(/\n/g, '<br>');
    }
    
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }
    
    // Cleanup
    destroy() {
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
        }
        
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        
        // Remove event listeners
        if (this.wrapper) {
            this.wrapper.removeEventListener('scroll', this.handleScroll);
            this.wrapper.removeEventListener('wheel', this.handleWheel);
        }
        
        if (this.scrollButton) {
            this.scrollButton.removeEventListener('click', this.scrollToBottom);
        }
        
        // Clear references
        this.messages = [];
        this.measuredHeights.clear();
        this.container = null;
        this.wrapper = null;
        this.content = null;
    }
    
    // Public API methods
    getMessageCount() {
        return this.messages.length;
    }
    
    getVisibleRange() {
        return {
            start: this.startIndex,
            end: this.endIndex,
            total: this.messages.length
        };
    }
    
    isAtBottom() {
        return this.isAutoScrollEnabled && 
               this.scrollTop + this.containerHeight >= this.totalHeight - this.config.scrollThreshold;
    }
    
    // Performance monitoring
    getPerformanceStats() {
        return {
            totalMessages: this.messages.length,
            visibleMessages: this.endIndex - this.startIndex + 1,
            measuredHeights: this.measuredHeights.size,
            totalHeight: this.totalHeight,
            containerHeight: this.containerHeight,
            memoryUsage: {
                messages: this.messages.length * 200, // Rough estimate in bytes
                heightCache: this.measuredHeights.size * 50
            }
        };
    }
}
//# sourceMappingURL=virtual-chat.js.map
