
// WebSocket service for real-time communication
export class WebSocketService {
    constructor() {
        this.socket = null;
        this.listeners = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
    }

    connect() {
        if (typeof io === 'undefined') {
            console.error('Socket.IO not loaded');
            setTimeout(() => this.connect(), 1000);
            return;
        }

        const url = window.location.hostname === 'localhost' 
            ? 'http://localhost:5006' 
            : window.location.origin;

        this.socket = io(url, {
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay
        });

        this.socket.on('connect', () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.emit('connected');
        });

        this.socket.on('disconnect', (reason) => {
            console.log('WebSocket disconnected:', reason);
            this.emit('disconnected');
            
            if (reason === 'io server disconnect') {
                // Server disconnected us, try to reconnect
                setTimeout(() => this.connect(), this.reconnectDelay);
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error.message);
            this.reconnectAttempts++;
            
            if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                console.error('Max reconnection attempts reached');
                this.emit('connection_failed');
            }
        });

        // Handle agent communication updates
        this.socket.on('agent_communication', (data) => {
            console.log('Agent communication event:', data);
            this.emit('agent_communication', data);
        });

        // Handle task progress updates
        this.socket.on('task_progress', (data) => {
            console.log('Task progress update:', data);
            this.emit('task_progress', data);
        });

        // Handle system notifications
        this.socket.on('system_notification', (data) => {
            console.log('System notification:', data);
            this.emit('system_notification', data);
        });
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
    }

    joinTask(taskId) {
        if (this.socket && this.socket.connected) {
            this.socket.emit('join_task', { task_id: taskId });
        } else {
            console.warn('Cannot join task - WebSocket not connected');
        }
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
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
}
