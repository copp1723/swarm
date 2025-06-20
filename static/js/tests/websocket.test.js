import { WebSocketService } from '../services/websocket.js';

// Mock Socket.IO
const mockSocket = {
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
    connected: true,
    id: 'test-socket-id'
};

global.io = jest.fn(() => mockSocket);

describe('WebSocketService', () => {
    let wsService;

    beforeEach(() => {
        jest.clearAllMocks();
        wsService = new WebSocketService();
    });

    describe('constructor', () => {
        it('should initialize with default values', () => {
            expect(wsService.socket).toBeNull();
            expect(wsService.reconnectAttempts).toBe(0);
            expect(wsService.maxReconnectAttempts).toBe(10);
            expect(wsService.baseReconnectDelay).toBe(1000);
            expect(wsService.maxReconnectDelay).toBe(30000);
            expect(wsService.isConnecting).toBe(false);
            expect(wsService.connectionState).toBe('disconnected');
            expect(wsService.autoReconnect).toBe(true);
            expect(wsService.connectionQuality).toBe('good');
        });
    });

    describe('connect', () => {
        it('should not connect if already connecting', () => {
            wsService.isConnecting = true;
            
            wsService.connect();
            
            expect(io).not.toHaveBeenCalled();
        });

        it('should not connect if already connected', () => {
            wsService.connectionState = 'connected';
            
            wsService.connect();
            
            expect(io).not.toHaveBeenCalled();
        });

        it('should create socket connection with correct URL and options', () => {
            wsService.connect();
            
            expect(io).toHaveBeenCalledWith('http://localhost:5006', {
                transports: ['websocket', 'polling'],
                reconnection: false,
                timeout: 20000,
                forceNew: true
            });
            
            expect(wsService.isConnecting).toBe(true);
            expect(wsService.connectionState).toBe('connecting');
        });

        it('should setup event handlers after creating socket', () => {
            wsService.connect();
            
            expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function));
            expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function));
            expect(mockSocket.on).toHaveBeenCalledWith('connect_error', expect.any(Function));
        });

        it('should retry connection if Socket.IO not loaded', (done) => {
            // Temporarily remove io global
            const originalIo = global.io;
            delete global.io;
            
            wsService.connect();
            
            setTimeout(() => {
                global.io = originalIo;
                expect(setTimeout).toHaveBeenCalled();
                done();
            }, 100);
        });
    });

    describe('event handling', () => {
        beforeEach(() => {
            wsService.connect();
        });

        it('should handle successful connection', () => {
            const connectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect')[1];
            const emitSpy = jest.spyOn(wsService, 'emit');
            
            connectHandler();
            
            expect(wsService.isConnecting).toBe(false);
            expect(wsService.connectionState).toBe('connected');
            expect(wsService.reconnectAttempts).toBe(0);
            expect(wsService.connectionQuality).toBe('good');
            expect(emitSpy).toHaveBeenCalledWith('connected', {
                sessionId: 'test-socket-id',
                connectionTime: expect.any(Number)
            });
        });

        it('should handle disconnection and schedule reconnect', () => {
            const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')[1];
            const scheduleReconnectSpy = jest.spyOn(wsService, 'scheduleReconnect');
            const emitSpy = jest.spyOn(wsService, 'emit');
            
            disconnectHandler('server disconnect');
            
            expect(wsService.isConnecting).toBe(false);
            expect(wsService.connectionState).toBe('disconnected');
            expect(emitSpy).toHaveBeenCalledWith('disconnected', { reason: 'server disconnect' });
            expect(scheduleReconnectSpy).toHaveBeenCalled();
        });

        it('should not schedule reconnect for manual disconnect', () => {
            const disconnectHandler = mockSocket.on.mock.calls.find(call => call[0] === 'disconnect')[1];
            const scheduleReconnectSpy = jest.spyOn(wsService, 'scheduleReconnect');
            
            disconnectHandler('io client disconnect');
            
            expect(scheduleReconnectSpy).not.toHaveBeenCalled();
        });

        it('should handle connection errors', () => {
            const errorHandler = mockSocket.on.mock.calls.find(call => call[0] === 'connect_error')[1];
            const scheduleReconnectSpy = jest.spyOn(wsService, 'scheduleReconnect');
            const emitSpy = jest.spyOn(wsService, 'emit');
            
            errorHandler(new Error('Connection failed'));
            
            expect(wsService.isConnecting).toBe(false);
            expect(wsService.connectionState).toBe('disconnected');
            expect(wsService.connectionQuality).toBe('poor');
            expect(emitSpy).toHaveBeenCalledWith('connection_error', {
                error: 'Connection failed',
                attempts: 0
            });
            expect(scheduleReconnectSpy).toHaveBeenCalled();
        });
    });

    describe('scheduleReconnect', () => {
        it('should schedule reconnect with exponential backoff', (done) => {
            wsService.reconnectAttempts = 2;
            wsService.baseReconnectDelay = 100;
            
            const emitSpy = jest.spyOn(wsService, 'emit');
            
            wsService.scheduleReconnect();
            
            expect(emitSpy).toHaveBeenCalledWith('reconnect_scheduled', {
                delay: expect.any(Number),
                attempt: 3,
                maxAttempts: 10
            });
            
            setTimeout(() => {
                expect(wsService.reconnectAttempts).toBe(3);
                done();
            }, 200);
        });

        it('should stop reconnecting after max attempts', () => {
            wsService.reconnectAttempts = 10;
            const emitSpy = jest.spyOn(wsService, 'emit');
            
            wsService.scheduleReconnect();
            
            expect(wsService.connectionQuality).toBe('offline');
            expect(emitSpy).toHaveBeenCalledWith('connection_failed', {
                maxAttemptsReached: true,
                attempts: 10
            });
        });
    });

    describe('disconnect', () => {
        beforeEach(() => {
            wsService.socket = mockSocket;
            wsService.connectionState = 'connected';
        });

        it('should disconnect socket and cleanup', () => {
            wsService.disconnect();
            
            expect(wsService.autoReconnect).toBe(false);
            expect(mockSocket.disconnect).toHaveBeenCalled();
            expect(wsService.socket).toBeNull();
            expect(wsService.connectionState).toBe('disconnected');
            expect(wsService.isConnecting).toBe(false);
        });
    });

    describe('reconnect', () => {
        it('should reset attempts and reconnect', () => {
            wsService.reconnectAttempts = 5;
            const disconnectSpy = jest.spyOn(wsService, 'disconnect');
            const connectSpy = jest.spyOn(wsService, 'connect');
            
            wsService.reconnect();
            
            expect(wsService.autoReconnect).toBe(true);
            expect(wsService.reconnectAttempts).toBe(0);
            expect(disconnectSpy).toHaveBeenCalled();
            
            setTimeout(() => {
                expect(connectSpy).toHaveBeenCalled();
            }, 1100);
        });
    });

    describe('getConnectionStatus', () => {
        it('should return current connection status', () => {
            wsService.connectionState = 'connected';
            wsService.connectionQuality = 'good';
            wsService.reconnectAttempts = 2;
            wsService.lastConnectionTime = 12345;
            
            const status = wsService.getConnectionStatus();
            
            expect(status).toEqual({
                state: 'connected',
                quality: 'good',
                reconnectAttempts: 2,
                maxReconnectAttempts: 10,
                lastConnectionTime: 12345,
                isAutoReconnectEnabled: true
            });
        });
    });

    describe('setAutoReconnect', () => {
        it('should enable/disable auto-reconnect', () => {
            wsService.setAutoReconnect(false);
            expect(wsService.autoReconnect).toBe(false);
            
            wsService.setAutoReconnect(true);
            expect(wsService.autoReconnect).toBe(true);
        });
    });

    describe('joinTask', () => {
        it('should join task if connected', () => {
            wsService.socket = mockSocket;
            
            wsService.joinTask('task-123');
            
            expect(mockSocket.emit).toHaveBeenCalledWith('join_task', {
                task_id: 'task-123'
            });
        });

        it('should queue join request if not connected', () => {
            wsService.socket = null;
            const onceSpy = jest.spyOn(wsService, 'once');
            
            wsService.joinTask('task-123');
            
            expect(onceSpy).toHaveBeenCalledWith('connected', expect.any(Function));
        });
    });

    describe('send', () => {
        it('should send message if connected', () => {
            wsService.socket = mockSocket;
            
            const result = wsService.send('test_event', { data: 'test' });
            
            expect(mockSocket.emit).toHaveBeenCalledWith('test_event', { data: 'test' });
            expect(result).toBe(true);
        });

        it('should return false if not connected', () => {
            wsService.socket = null;
            
            const result = wsService.send('test_event', { data: 'test' });
            
            expect(result).toBe(false);
        });
    });

    describe('event listeners', () => {
        it('should add event listeners', () => {
            const callback = jest.fn();
            
            wsService.on('test_event', callback);
            
            expect(wsService.listeners.get('test_event')).toContain(callback);
        });

        it('should remove event listeners', () => {
            const callback = jest.fn();
            wsService.on('test_event', callback);
            
            wsService.off('test_event', callback);
            
            const listeners = wsService.listeners.get('test_event');
            expect(listeners).not.toContain(callback);
        });

        it('should emit events to listeners', () => {
            const callback1 = jest.fn();
            const callback2 = jest.fn();
            
            wsService.on('test_event', callback1);
            wsService.on('test_event', callback2);
            
            wsService.emit('test_event', { data: 'test' });
            
            expect(callback1).toHaveBeenCalledWith({ data: 'test' });
            expect(callback2).toHaveBeenCalledWith({ data: 'test' });
        });

        it('should handle listener errors gracefully', () => {
            const errorCallback = jest.fn(() => {
                throw new Error('Listener error');
            });
            const goodCallback = jest.fn();
            
            wsService.on('test_event', errorCallback);
            wsService.on('test_event', goodCallback);
            
            wsService.emit('test_event', { data: 'test' });
            
            expect(errorCallback).toHaveBeenCalled();
            expect(goodCallback).toHaveBeenCalled();
        });

        it('should support once listeners', () => {
            const callback = jest.fn();
            
            wsService.once('test_event', callback);
            
            wsService.emit('test_event', { data: 'test1' });
            wsService.emit('test_event', { data: 'test2' });
            
            expect(callback).toHaveBeenCalledTimes(1);
            expect(callback).toHaveBeenCalledWith({ data: 'test1' });
        });
    });

    describe('destroy', () => {
        it('should cleanup all resources', () => {
            wsService.socket = mockSocket;
            wsService.connectionRetryTimer = setTimeout(() => {}, 1000);
            wsService.on('test_event', jest.fn());
            
            const disconnectSpy = jest.spyOn(wsService, 'disconnect');
            
            wsService.destroy();
            
            expect(wsService.autoReconnect).toBe(false);
            expect(disconnectSpy).toHaveBeenCalled();
            expect(wsService.listeners.size).toBe(0);
        });
    });
});

