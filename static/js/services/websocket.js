// @ts-check
// WebSocket service with exponential backoff auto-reconnect

/**
 * WebSocket service class providing resilient real-time communication
 * Features exponential backoff, health monitoring, and event management
 * Follows UI/Frontend Rules for WebSocket resilience with auto-reconnect
 */
export class WebSocketService {
    constructor() {
        /** @type {any|null} Socket.IO connection instance */
        this.socket = null;
        /** @type {Map<string, Function[]>} Event listeners map */
        this.listeners = new Map();
        /** @type {number} Current reconnection attempt count */
        this.reconnectAttempts = 0;
        /** @type {number} Maximum reconnection attempts before giving up */
        this.maxReconnectAttempts = 10;
        /** @type {number} Base delay for exponential backoff (1 second) */
        this.baseReconnectDelay = 1000;
        /** @type {number} Maximum reconnection delay (30 seconds) */
        this.maxReconnectDelay = 30000;
        /** @type {boolean} Whether currently attempting to connect */
        this.isConnecting = false;
        /** @type {number|null} Timer ID for connection retry */
        this.connectionRetryTimer = null;
        /** @type {number|null} Timestamp of last successful connection */
        this.lastConnectionTime = null;
        /** @type {'disconnected'|'connecting'|'connected'} Connection state */
        this.connectionState = 'disconnected';
        /** @type {boolean} Whether to automatically reconnect on disconnect */
        this.autoReconnect = true;
        /** @type {'good'|'poor'|'offline'} Connection quality indicator */
        this.connectionQuality = 'good';
        /** @type {number|null} Health check interval timer ID */
        this.healthCheckInterval = null;
    }

    /**
     * Establish WebSocket connection with auto-reconnect logic
     * Implements exponential backoff and connection resilience per Core Development Rules
     * @returns {void}
     */
    connect() {
        if (this.isConnecting || this.connectionState === 'connected') {
            console.log('Already connecting or connected');
            return;
        }

        if (typeof io === 'undefined') {
            console.error('Socket.IO not loaded, retrying in 2 seconds...');
            setTimeout(() => this.connect(), 2000);
            return;
        }

        this.isConnecting = true;
        this.connectionState = 'connecting';
        
        // Clear any existing retry timer
        if (this.connectionRetryTimer) {
            clearTimeout(this.connectionRetryTimer);
            this.connectionRetryTimer = null;
        }

        const url = window.location.hostname === 'localhost' 
            ? 'http://localhost:5006' 
            : window.location.origin;

        console.log(`Attempting WebSocket connection (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
        
        // Disable built-in reconnection to handle our own
        this.socket = io(url, {
            transports: ['websocket', 'polling'],
            reconnection: false, // We handle reconnection ourselves
            timeout: 20000,
            forceNew: true
        });

        // Set up event handlers
        this.setupEventHandlers();
    }

    /**
     * Set up all WebSocket event handlers for connection lifecycle and app events
     * Handles connect, disconnect, errors, and application-specific events
     * @private
     */
    setupEventHandlers() {
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected successfully');
            this.isConnecting = false;
            this.connectionState = 'connected';
            this.reconnectAttempts = 0;
            this.lastConnectionTime = Date.now();
            this.connectionQuality = 'good';
            
            // Start health monitoring
            this.startHealthCheck();
            
            this.emit('connected', {
                sessionId: this.socket.id,
                connectionTime: this.lastConnectionTime
            });
        });

        this.socket.on('disconnect', (reason) => {
            console.log(`🔌 WebSocket disconnected: ${reason}`);
            this.isConnecting = false;
            this.connectionState = 'disconnected';
            
            // Stop health monitoring
            this.stopHealthCheck();
            
            this.emit('disconnected', { reason });
            
            // Auto-reconnect unless explicitly disabled or server forced disconnect
            if (this.autoReconnect && reason !== 'io client disconnect') {
                this.scheduleReconnect();
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error(`❌ WebSocket connection error: ${error.message}`);
            this.isConnecting = false;
            this.connectionState = 'disconnected';
            this.connectionQuality = 'poor';
            
            this.emit('connection_error', { error: error.message, attempts: this.reconnectAttempts });
            
            if (this.autoReconnect) {
                this.scheduleReconnect();
            }
        });

        this.socket.on('reconnect_error', (error) => {
            console.error(`🔄 WebSocket reconnection error: ${error.message}`);
            this.connectionQuality = 'offline';
        });

        // Application-specific event handlers
        this.socket.on('connected', (data) => {
            console.log('📡 Server confirmed connection:', data);
            this.emit('server_connected', data);
        });

        this.socket.on('agent_communication', (data) => {
            console.log('🤖 Agent communication event:', data);
            this.emit('agent_communication', data);
        });

        this.socket.on('task_progress', (data) => {
            console.log('📊 Task progress update:', data);
            this.emit('task_progress', data);
        });

        this.socket.on('system_notification', (data) => {
            console.log('🔔 System notification:', data);
            this.emit('system_notification', data);
        });

        this.socket.on('task_complete', (data) => {
            console.log('✅ Task complete event:', data);
            this.emit('task_complete', data);
        });

        this.socket.on('task_error', (data) => {
            console.log('❌ Task error event:', data);
            this.emit('task_error', data);
        });

        this.socket.on('error', (error) => {
            console.error('⚠️ Socket error:', error);
            this.emit('socket_error', { error });
        });
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`❌ Max reconnection attempts (${this.maxReconnectAttempts}) reached. Giving up.`);
            this.connectionQuality = 'offline';
            this.emit('connection_failed', { 
                maxAttemptsReached: true, 
                attempts: this.reconnectAttempts 
            });
            return;
        }

        // Calculate exponential backoff delay with jitter
        const exponentialDelay = Math.min(
            this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        
        // Add jitter (±25%) to avoid thundering herd
        const jitter = exponentialDelay * 0.25 * (Math.random() - 0.5);
        const delayWithJitter = Math.round(exponentialDelay + jitter);
        
        console.log(`🔄 Scheduling reconnect in ${delayWithJitter}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
        
        this.connectionRetryTimer = setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delayWithJitter);
        
        this.emit('reconnect_scheduled', { 
            delay: delayWithJitter, 
            attempt: this.reconnectAttempts + 1, 
            maxAttempts: this.maxReconnectAttempts 
        });
    }

    startHealthCheck() {
        // Ping the server every 30 seconds to check connection health
        this.healthCheckInterval = setInterval(() => {
            if (this.socket && this.socket.connected) {
                const pingStart = Date.now();
                this.socket.emit('ping', { timestamp: pingStart });
                
                // Set up one-time pong listener
                const pongTimeout = setTimeout(() => {
                    console.warn('⚠️ Ping timeout - connection may be degraded');
                    this.connectionQuality = 'poor';
                }, 5000);
                
                this.socket.once('pong', (data) => {
                    clearTimeout(pongTimeout);
                    const latency = Date.now() - pingStart;
                    this.connectionQuality = latency < 1000 ? 'good' : 'poor';
                    console.log(`🏓 Ping: ${latency}ms`);
                });
            }
        }, 30000);
    }

    stopHealthCheck() {
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
            this.healthCheckInterval = null;
        }
    }

    disconnect() {
        console.log('🔌 Manually disconnecting WebSocket');
        this.autoReconnect = false; // Disable auto-reconnect for manual disconnect
        
        // Clear any pending reconnection
        if (this.connectionRetryTimer) {
            clearTimeout(this.connectionRetryTimer);
            this.connectionRetryTimer = null;
        }
        
        // Stop health monitoring
        this.stopHealthCheck();
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        this.connectionState = 'disconnected';
        this.isConnecting = false;
    }

    // Manual reconnect method
    reconnect() {
        console.log('🔄 Manual reconnect requested');
        this.autoReconnect = true;
        this.reconnectAttempts = 0; // Reset attempt counter
        this.disconnect();
        setTimeout(() => this.connect(), 1000);
    }

    // Get connection status
    getConnectionStatus() {
        return {
            state: this.connectionState,
            quality: this.connectionQuality,
            reconnectAttempts: this.reconnectAttempts,
            maxReconnectAttempts: this.maxReconnectAttempts,
            lastConnectionTime: this.lastConnectionTime,
            isAutoReconnectEnabled: this.autoReconnect
        };
    }

    // Enable/disable auto-reconnect
    setAutoReconnect(enabled) {
        this.autoReconnect = enabled;
        console.log(`Auto-reconnect ${enabled ? 'enabled' : 'disabled'}`);
    }

    joinTask(taskId) {
        if (this.socket && this.socket.connected) {
            console.log(`📋 Joining task room: ${taskId}`);
            this.socket.emit('join_task', { task_id: taskId });
        } else {
            console.warn('Cannot join task - WebSocket not connected');
            // Queue the join request for when connection is established
            this.once('connected', () => {
                this.joinTask(taskId);
            });
        }
    }

    leaveTask(taskId) {
        if (this.socket && this.socket.connected) {
            console.log(`📋 Leaving task room: ${taskId}`);
            this.socket.emit('leave_task_room', { task_id: taskId });
        }
    }

    // Event listener management
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    once(event, callback) {
        const onceCallback = (data) => {
            callback(data);
            this.off(event, onceCallback);
        };
        this.on(event, onceCallback);
    }

    off(event, callback) {
        if (this.listeners.has(event)) {
            const callbacks = this.listeners.get(event);
            const index = callbacks.indexOf(callback);
            if (index > -1) {
                callbacks.splice(index, 1);
            }
        }
    }

    emit(event, data) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (err) {
                    console.error(`Error in WebSocket listener for ${event}:`, err);
                }
            });
        }
    }

    // Send a message to the server (if connected)
    send(event, data) {
        if (this.socket && this.socket.connected) {
            this.socket.emit(event, data);
        } else {
            console.warn(`Cannot send ${event} - WebSocket not connected`);
            return false;
        }
        return true;
    }

    // Cleanup method
    destroy() {
        console.log('🧹 Destroying WebSocket service');
        this.autoReconnect = false;
        
        if (this.connectionRetryTimer) {
            clearTimeout(this.connectionRetryTimer);
        }
        
        this.stopHealthCheck();
        this.disconnect();
        this.listeners.clear();
    }
}

//# sourceMappingURL=websocket.js.map
