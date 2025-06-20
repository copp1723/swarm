import { ChatInterface } from '../components/chat-interface.js';

// Mock dependencies
jest.mock('../services/api.js', () => ({
    AgentAPI: jest.fn().mockImplementation(() => ({
        sendMessage: jest.fn(),
        uploadFile: jest.fn(),
        getChatHistory: jest.fn(),
        clearChatHistory: jest.fn()
    }))
}));

jest.mock('../services/storage.js', () => ({
    StorageService: jest.fn().mockImplementation(() => ({
        getAgentDirectory: jest.fn(),
        setAgentDirectory: jest.fn(),
        getModelPreference: jest.fn(() => 'openai/gpt-4.1'),
        setModelPreference: jest.fn(),
        getEnhancePromptSetting: jest.fn(() => true)
    }))
}));

jest.mock('../components/directory-browser.js', () => ({
    DirectoryBrowser: jest.fn().mockImplementation(() => ({
        open: jest.fn()
    }))
}));

jest.mock('../agents/agent-config.js', () => ({
    getAgentById: jest.fn((id) => ({
        id,
        name: 'Test Agent',
        role: 'Testing',
        color: 'blue'
    })),
    getAgentColor: jest.fn(() => 'bg-blue-500'),
    AGENTS: [
        { id: 'test_01', name: 'Test Agent', role: 'Testing' }
    ]
}));

describe('ChatInterface', () => {
    let chatInterface;
    let mockAgentAPI;

    beforeEach(() => {
        chatInterface = new ChatInterface('test_01');
        mockAgentAPI = chatInterface.api;
        
        // Mock DOM elements
        document.getElementById = jest.fn((id) => {
            const mockElement = {
                innerHTML: '',
                textContent: '',
                value: '',
                addEventListener: jest.fn(),
                appendChild: jest.fn(),
                querySelector: jest.fn(),
                querySelectorAll: jest.fn(() => []),
                classList: {
                    add: jest.fn(),
                    remove: jest.fn(),
                    contains: jest.fn()
                },
                style: {},
                focus: jest.fn(),
                scrollTop: 0,
                scrollHeight: 100
            };
            
            if (id.includes('input-')) {
                mockElement.addEventListener = jest.fn();
            }
            
            return mockElement;
        });
    });

    describe('constructor', () => {
        it('should initialize with correct agent data', () => {
            expect(chatInterface.agentId).toBe('test_01');
            expect(chatInterface.agent).toEqual({
                id: 'test_01',
                name: 'Test Agent',
                role: 'Testing',
                color: 'blue'
            });
        });
    });

    describe('sendMessage', () => {
        beforeEach(() => {
            chatInterface.setupElements();
            chatInterface.input = { value: 'Test message', addEventListener: jest.fn() };
            chatInterface.modelSelector = { value: 'openai/gpt-4.1' };
            chatInterface.chatArea = {
                appendChild: jest.fn(),
                scrollTop: 0,
                scrollHeight: 100
            };
        });

        it('should not send empty messages', async () => {
            chatInterface.input.value = '   ';
            
            await chatInterface.sendMessage();
            
            expect(mockAgentAPI.sendMessage).not.toHaveBeenCalled();
        });

        it('should send message with working directory context', async () => {
            chatInterface.workingDirectory = '/test/path';
            chatInterface.input.value = 'Test message';
            
            mockAgentAPI.sendMessage.mockResolvedValue({
                success: true,
                response: 'Test response'
            });
            
            await chatInterface.sendMessage();
            
            expect(mockAgentAPI.sendMessage).toHaveBeenCalledWith(
                'test_01',
                '[Working in: /test/path]\nTest message',
                'openai/gpt-4.1',
                true
            );
        });

        it('should handle API errors gracefully', async () => {
            chatInterface.input.value = 'Test message';
            mockAgentAPI.sendMessage.mockRejectedValue(new Error('API Error'));
            
            const addMessageSpy = jest.spyOn(chatInterface, 'addMessage');
            
            await chatInterface.sendMessage();
            
            expect(addMessageSpy).toHaveBeenCalledWith('Failed to send message', 'error');
        });

        it('should detect and handle agent mentions', async () => {
            chatInterface.input.value = 'Hey @testAgent, can you help?';
            
            const addMessageSpy = jest.spyOn(chatInterface, 'addMessage');
            
            await chatInterface.sendMessage();
            
            expect(addMessageSpy).toHaveBeenCalledWith(
                'Hey @testAgent, can you help?',
                'user'
            );
        });
    });

    describe('addMessage', () => {
        beforeEach(() => {
            chatInterface.chatArea = {
                appendChild: jest.fn(),
                scrollTop: 0,
                scrollHeight: 100
            };
        });

        it('should add user message with correct styling', () => {
            chatInterface.addMessage('Test message', 'user');
            
            expect(chatInterface.chatArea.appendChild).toHaveBeenCalled();
        });

        it('should add assistant message with agent name', () => {
            chatInterface.addMessage('Test response', 'assistant');
            
            expect(chatInterface.chatArea.appendChild).toHaveBeenCalled();
        });

        it('should add error message with error styling', () => {
            chatInterface.addMessage('Error occurred', 'error');
            
            expect(chatInterface.chatArea.appendChild).toHaveBeenCalled();
        });

        it('should scroll to bottom after adding message', () => {
            chatInterface.addMessage('Test message', 'user');
            
            expect(chatInterface.chatArea.scrollTop).toBe(100);
        });
    });

    describe('loadChatHistory', () => {
        beforeEach(() => {
            chatInterface.chatArea = {
                innerHTML: '',
                appendChild: jest.fn()
            };
        });

        it('should load and display chat history', async () => {
            const mockHistory = {
                success: true,
                history: [
                    { role: 'user', content: 'Hello' },
                    { role: 'assistant', content: 'Hi there!' }
                ]
            };
            
            mockAgentAPI.getChatHistory.mockResolvedValue(mockHistory);
            const addMessageSpy = jest.spyOn(chatInterface, 'addMessage');
            
            await chatInterface.loadChatHistory();
            
            expect(addMessageSpy).toHaveBeenCalledTimes(2);
            expect(addMessageSpy).toHaveBeenCalledWith('Hello', 'user');
            expect(addMessageSpy).toHaveBeenCalledWith('Hi there!', 'assistant');
        });

        it('should handle empty chat history', async () => {
            mockAgentAPI.getChatHistory.mockResolvedValue({
                success: true,
                history: []
            });
            
            await chatInterface.loadChatHistory();
            
            expect(chatInterface.chatArea.innerHTML).toBe('');
        });

        it('should handle API errors gracefully', async () => {
            mockAgentAPI.getChatHistory.mockRejectedValue(new Error('API Error'));
            
            await chatInterface.loadChatHistory();
            
            expect(console.error).toHaveBeenCalled();
        });
    });

    describe('clearChat', () => {
        beforeEach(() => {
            chatInterface.chatArea = { innerHTML: '' };
            global.confirm = jest.fn(() => true);
        });

        it('should clear chat after confirmation', async () => {
            mockAgentAPI.clearChatHistory.mockResolvedValue(true);
            
            await chatInterface.clearChat();
            
            expect(mockAgentAPI.clearChatHistory).toHaveBeenCalledWith('test_01');
            expect(chatInterface.chatArea.innerHTML).toContain('No messages yet');
        });

        it('should not clear chat if user cancels', async () => {
            global.confirm = jest.fn(() => false);
            
            await chatInterface.clearChat();
            
            expect(mockAgentAPI.clearChatHistory).not.toHaveBeenCalled();
        });
    });

    describe('uploadFile', () => {
        beforeEach(() => {
            chatInterface.chatArea = {
                appendChild: jest.fn(),
                scrollTop: 0,
                scrollHeight: 100
            };
        });

        it('should upload file successfully', async () => {
            const mockFile = new File(['content'], 'test.txt', { type: 'text/plain' });
            
            document.getElementById.mockImplementation((id) => {
                if (id.includes('upload-')) {
                    return { files: [mockFile], value: '' };
                }
                if (id.includes('file-label-')) {
                    return { textContent: '' };
                }
                return { textContent: '' };
            });
            
            mockAgentAPI.uploadFile.mockResolvedValue({
                success: true,
                agent_response: 'File uploaded successfully'
            });
            
            const addMessageSpy = jest.spyOn(chatInterface, 'addMessage');
            
            await chatInterface.uploadFile();
            
            expect(mockAgentAPI.uploadFile).toHaveBeenCalledWith('test_01', mockFile);
            expect(addMessageSpy).toHaveBeenCalledWith('File uploaded successfully', 'assistant');
        });

        it('should handle no file selected', async () => {
            document.getElementById.mockImplementation(() => ({ files: [] }));
            
            await chatInterface.uploadFile();
            
            expect(mockAgentAPI.uploadFile).not.toHaveBeenCalled();
        });
    });

    describe('show and hide', () => {
        beforeEach(() => {
            chatInterface.container = {
                classList: {
                    add: jest.fn(),
                    remove: jest.fn()
                }
            };
            chatInterface.input = { focus: jest.fn() };
        });

        it('should show chat interface', () => {
            chatInterface.show();
            
            expect(chatInterface.container.classList.add).toHaveBeenCalledWith('active');
            expect(chatInterface.isActive).toBe(true);
        });

        it('should hide chat interface', () => {
            chatInterface.hide();
            
            expect(chatInterface.container.classList.remove).toHaveBeenCalledWith('active');
            expect(chatInterface.isActive).toBe(false);
        });
    });
});

