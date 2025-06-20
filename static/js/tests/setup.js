// Test environment setup for Jest + jsdom

// Mock external dependencies
global.fetch = jest.fn();
global.localStorage = {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
    clear: jest.fn()
};

// Mock Lucide icons
global.lucide = {
    createIcons: jest.fn()
};

// Mock WebSocket/Socket.IO
global.io = jest.fn(() => ({
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
    connected: true,
    id: 'test-socket-id'
}));

// Mock DOM APIs
Object.defineProperty(window, 'location', {
    value: {
        hostname: 'localhost',
        origin: 'http://localhost:5006'
    },
    writable: true
});

// Mock Navigator API for clipboard
Object.defineProperty(navigator, 'clipboard', {
    value: {
        writeText: jest.fn(() => Promise.resolve())
    },
    writable: true
});

// Mock console methods for test cleanliness
const originalConsole = global.console;
global.console = {
    ...originalConsole,
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn()
};

// Setup DOM environment
beforeEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    fetch.mockClear();
});

// Cleanup after tests
afterEach(() => {
    jest.clearAllMocks();
});

