/**
 * WebSocket Auto-Reconnect Demo
 * Demonstrates the exponential backoff auto-reconnect functionality
 * Required by UI/Frontend Rules
 */

import { WebSocketService } from '../services/websocket.js';

class WebSocketDemo {
    constructor() {
        this.ws = new WebSocketService();
        this.logContainer = null;
        this.statusContainer = null;
        this.reconnectCounter = 0;
        this.isDemo = true;
    }

    init() {
        this.createDemoInterface();
        this.setupEventListeners();
        this.startDemo();
    }

    createDemoInterface() {
        // Create demo container
        const demoContainer = document.createElement('div');
        demoContainer.className = 'websocket-demo p-6 bg-gray-100 rounded-lg';
        demoContainer.innerHTML = `
            <h3 class="text-xl font-bold mb-4">🔌 WebSocket Auto-Reconnect Demo</h3>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Status Panel -->
                <div class="bg-white p-4 rounded-lg shadow">
                    <h4 class="font-semibold mb-3">Connection Status</h4>
                    <div id="ws-status" class="mb-4"></div>
                    
                    <div class="space-y-2">
                        <button id="connect-btn" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                            Connect
                        </button>
                        <button id="disconnect-btn" class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                            Disconnect
                        </button>
                        <button id="reconnect-btn" class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                            Manual Reconnect
                        </button>
                        <button id="test-resilience-btn" class="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600">
                            Test Resilience
                        </button>
                    </div>
                </div>
                
                <!-- Log Panel -->
                <div class="bg-white p-4 rounded-lg shadow">
                    <h4 class="font-semibold mb-3">Connection Log</h4>
                    <div id="ws-log" class="h-64 overflow-y-auto bg-gray-50 p-2 rounded text-sm font-mono"></div>
                    <button id="clear-log-btn" class="mt-2 bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600">
                        Clear Log
                    </button>
                </div>
            </div>
            
            <!-- Metrics Panel -->
            <div class="mt-6 bg-white p-4 rounded-lg shadow">
                <h4 class="font-semibold mb-3">📊 Metrics</h4>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div class="text-center">
                        <div class="text-2xl font-bold text-blue-600" id="reconnect-attempts">0</div>
                        <div class="text-sm text-gray-600">Reconnect Attempts</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-green-600" id="successful-connections">0</div>
                        <div class="text-sm text-gray-600">Successful Connections</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-orange-600" id="connection-quality">-</div>
                        <div class="text-sm text-gray-600">Connection Quality</div>
                    </div>
                    <div class="text-center">
                        <div class="text-2xl font-bold text-purple-600" id="uptime">0s</div>
                        <div class="text-sm text-gray-600">Uptime</div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(demoContainer);
        
        this.logContainer = document.getElementById('ws-log');
        this.statusContainer = document.getElementById('ws-status');
    }

    setupEventListeners() {
        // Button event listeners
        document.getElementById('connect-btn').addEventListener('click', () => {
            this.log('🔗 Manual connect requested');
            this.ws.connect();
        });

        document.getElementById('disconnect-btn').addEventListener('click', () => {
            this.log('🔌 Manual disconnect requested');
            this.ws.disconnect();
        });

        document.getElementById('reconnect-btn').addEventListener('click', () => {
            this.log('🔄 Manual reconnect requested');
            this.ws.reconnect();
        });

        document.getElementById('test-resilience-btn').addEventListener('click', () => {
            this.testResilience();
        });

        document.getElementById('clear-log-btn').addEventListener('click', () => {
            this.logContainer.innerHTML = '';
        });

        // WebSocket event listeners (demonstrating auto-reconnect)
        this.ws.on('connected', (data) => {
            this.log(`✅ Connected successfully`, 'success');
            this.log(`   Session ID: ${data.sessionId}`, 'info');
            this.updateStatus('Connected', 'success');
            this.updateMetric('successful-connections', this.getSuccessfulConnections() + 1);
            this.startUptimeCounter();
        });

        this.ws.on('disconnected', (data) => {
            this.log(`🔌 Disconnected: ${data.reason}`, 'warning');
            this.updateStatus('Disconnected', 'error');
            this.stopUptimeCounter();
        });

        this.ws.on('connection_error', (data) => {
            this.log(`❌ Connection error: ${data.error}`, 'error');
            this.log(`   Attempt ${data.attempts} failed`, 'error');
            this.updateStatus('Connection Error', 'error');
        });

        this.ws.on('reconnect_scheduled', (data) => {
            this.log(`🔄 Reconnect scheduled in ${data.delay}ms (attempt ${data.attempt}/${data.maxAttempts})`, 'info');
            this.log(`   Using exponential backoff with jitter`, 'info');
            this.updateStatus(`Reconnecting in ${Math.round(data.delay / 1000)}s...`, 'warning');
            this.updateMetric('reconnect-attempts', data.attempt);
        });

        this.ws.on('connection_failed', (data) => {
            this.log(`💀 Connection failed permanently after ${data.attempts} attempts`, 'error');
            this.updateStatus('Connection Failed', 'error');
        });

        this.ws.on('server_connected', (data) => {
            this.log(`📡 Server confirmed connection`, 'success');
            this.log(`   Message: ${data.message}`, 'info');
        });
    }

    startDemo() {
        this.log('🚀 WebSocket Auto-Reconnect Demo Started', 'info');
        this.log('This demo showcases the exponential backoff auto-reconnect functionality', 'info');
        this.log('required by the UI/Frontend Rules', 'info');
        this.log('');
        
        // Start with initial connection
        setTimeout(() => {
            this.log('🔗 Initiating connection...');
            this.ws.connect();
        }, 1000);
    }

    testResilience() {
        this.log('🧪 Testing connection resilience...', 'info');
        this.log('This will simulate network issues and recovery', 'info');
        
        // Disconnect and let auto-reconnect handle it
        if (this.ws.getConnectionStatus().state === 'connected') {
            this.log('1. Simulating network disconnection...', 'warning');
            this.ws.socket.disconnect(); // Force disconnect without disabling auto-reconnect
        } else {
            this.log('1. Connection not established, testing from disconnected state...', 'info');
            this.ws.connect();
        }
    }

    log(message, type = 'default') {
        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        
        const colors = {
            success: 'text-green-600',
            error: 'text-red-600',
            warning: 'text-yellow-600',
            info: 'text-blue-600',
            default: 'text-gray-800'
        };
        
        entry.className = colors[type] || colors.default;
        entry.textContent = `[${timestamp}] ${message}`;
        
        this.logContainer.appendChild(entry);
        this.logContainer.scrollTop = this.logContainer.scrollHeight;
    }

    updateStatus(status, type) {
        const colors = {
            success: 'bg-green-100 text-green-800',
            error: 'bg-red-100 text-red-800',
            warning: 'bg-yellow-100 text-yellow-800',
            info: 'bg-blue-100 text-blue-800'
        };
        
        this.statusContainer.className = `px-3 py-2 rounded ${colors[type] || colors.info}`;
        this.statusContainer.textContent = status;
        
        // Update connection quality
        const wsStatus = this.ws.getConnectionStatus();
        document.getElementById('connection-quality').textContent = wsStatus.quality.toUpperCase();
    }

    updateMetric(metricId, value) {
        const element = document.getElementById(metricId);
        if (element) {
            element.textContent = value;
        }
    }

    getSuccessfulConnections() {
        const element = document.getElementById('successful-connections');
        return parseInt(element.textContent) || 0;
    }

    startUptimeCounter() {
        this.uptimeStart = Date.now();
        this.uptimeInterval = setInterval(() => {
            const uptime = Math.floor((Date.now() - this.uptimeStart) / 1000);
            this.updateMetric('uptime', `${uptime}s`);
        }, 1000);
    }

    stopUptimeCounter() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
            this.uptimeInterval = null;
        }
    }

    destroy() {
        this.stopUptimeCounter();
        this.ws.destroy();
    }
}

// Export for use
window.WebSocketDemo = WebSocketDemo;

// Auto-start demo if this script is loaded directly
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        const demo = new WebSocketDemo();
        demo.init();
        
        // Store for manual access
        window.wsDemo = demo;
    });
} else {
    const demo = new WebSocketDemo();
    demo.init();
    window.wsDemo = demo;
}

