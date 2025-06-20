import { AgentManager } from '../agents/agent-manager.js';
import { AGENTS } from '../agents/agent-config.js';

// Mock the config module
jest.mock('../config.js', () => ({
    getAuthHeaders: jest.fn(() => ({
        'Content-Type': 'application/json',
        'X-API-Key': 'test-key'
    }))
}));

// Mock DOM methods
const mockDOM = {
    getElementById: jest.fn(),
    querySelector: jest.fn(),
    querySelectorAll: jest.fn(() => []),
    addEventListener: jest.fn(),
    appendChild: jest.fn(),
    innerHTML: ''
};

Object.assign(document, mockDOM);

describe('AgentManager', () => {
    let agentManager;
    
    beforeEach(() => {
        agentManager = new AgentManager();
        
        // Mock DOM elements
        document.getElementById.mockImplementation((id) => {
            const mockElement = {
                innerHTML: '',
                appendChild: jest.fn(),
                addEventListener: jest.fn(),
                classList: {
                    add: jest.fn(),
                    remove: jest.fn(),
                    toggle: jest.fn(),
                    contains: jest.fn()
                },
                style: {},
                textContent: '',
                className: '',
                focus: jest.fn()
            };
            
            if (id === 'agent-nav-list' || id === 'agent-chats-container') {
                return mockElement;
            }
            
            return mockElement;
        });
        
        document.querySelector.mockReturnValue({
            classList: {
                add: jest.fn(),
                remove: jest.fn(),
                toggle: jest.fn()
            }
        });
    });

    describe('loadAgents', () => {
        it('should load agents from API successfully', async () => {
            const mockApiResponse = {
                success: true,
                profiles: [
                    {
                        agent_id: 'test_agent_01',
                        name: 'Test Agent',
                        description: 'Test description',
                        role: 'tester'
                    }
                ]
            };

            fetch.mockResolvedValueOnce({
                json: () => Promise.resolve(mockApiResponse)
            });

            await agentManager.loadAgents();

            expect(fetch).toHaveBeenCalledWith('/api/agents/list', {
                headers: {
                    'Content-Type': 'application/json',
                    'X-API-Key': 'test-key'
                }
            });

            expect(agentManager.agents).toHaveLength(1);
            expect(agentManager.agents[0]).toEqual({
                id: 'test_agent_01',
                name: 'Test Agent',
                role: 'Test description',
                icon: 'bug',
                color: 'red'
            });
        });

        it('should fallback to hardcoded agents on API failure', async () => {
            fetch.mockRejectedValueOnce(new Error('API Error'));

            await agentManager.loadAgents();

            expect(agentManager.agents).toEqual(AGENTS);
        });

        it('should use backend-provided agent_id instead of hardcoded mapping', async () => {
            const mockApiResponse = {
                success: true,
                profiles: [
                    {
                        agent_id: 'backend_provided_id',
                        name: 'Product Agent',
                        description: 'Product management',
                        role: 'product'
                    }
                ]
            };

            fetch.mockResolvedValueOnce({
                json: () => Promise.resolve(mockApiResponse)
            });

            await agentManager.loadAgents();

            expect(agentManager.agents[0].id).toBe('backend_provided_id');
        });
    });

    describe('selectAgent', () => {
        beforeEach(async () => {
            // Mock successful agent loading
            fetch.mockResolvedValueOnce({
                json: () => Promise.resolve({
                    success: true,
                    profiles: [{
                        agent_id: 'test_01',
                        name: 'Test Agent',
                        description: 'Test',
                        role: 'tester'
                    }]
                })
            });
            
            await agentManager.init();
        });

        it('should hide welcome message when agent is selected', () => {
            const welcomeElement = { style: { display: 'block' } };
            document.getElementById.mockReturnValue(welcomeElement);

            agentManager.selectAgent('test_01');

            expect(welcomeElement.style.display).toBe('none');
        });

        it('should update sidebar active state', () => {
            const mockNavItem = {
                classList: { add: jest.fn(), remove: jest.fn() }
            };
            document.getElementById.mockReturnValue(mockNavItem);
            
            agentManager.selectAgent('test_01');

            expect(mockNavItem.classList.add).toHaveBeenCalledWith('active');
        });

        it('should close mobile sidebar on mobile screens', () => {
            // Mock mobile screen width
            Object.defineProperty(window, 'innerWidth', {
                writable: true,
                configurable: true,
                value: 600
            });

            const sidebarElement = {
                classList: { remove: jest.fn() }
            };
            document.getElementById.mockReturnValue(sidebarElement);

            agentManager.selectAgent('test_01');

            expect(sidebarElement.classList.remove).toHaveBeenCalledWith('open');
        });
    });

    describe('toggleMobileSidebar', () => {
        it('should toggle sidebar open class', () => {
            const sidebarElement = {
                classList: { toggle: jest.fn() }
            };
            document.getElementById.mockReturnValue(sidebarElement);

            agentManager.toggleMobileSidebar();

            expect(sidebarElement.classList.toggle).toHaveBeenCalledWith('open');
        });

        it('should handle missing sidebar element gracefully', () => {
            document.getElementById.mockReturnValue(null);

            expect(() => {
                agentManager.toggleMobileSidebar();
            }).not.toThrow();
        });
    });

    describe('getIconForRole', () => {
        it('should return correct icons for known roles', () => {
            expect(agentManager.getIconForRole('product')).toBe('package');
            expect(agentManager.getIconForRole('developer')).toBe('code');
            expect(agentManager.getIconForRole('qa')).toBe('bug');
        });

        it('should return default icon for unknown roles', () => {
            expect(agentManager.getIconForRole('unknown')).toBe('message-circle');
        });
    });

    describe('updateAgentStatus', () => {
        it('should update agent status indicators', () => {
            const statusIndicator = {
                classList: {
                    remove: jest.fn(),
                    add: jest.fn()
                }
            };
            
            const navItem = {
                querySelector: jest.fn(() => statusIndicator)
            };
            
            document.getElementById.mockReturnValue(navItem);

            agentManager.updateAgentStatus('test_01', true);

            expect(statusIndicator.classList.remove).toHaveBeenCalledWith('bg-gray-500');
            expect(statusIndicator.classList.add).toHaveBeenCalledWith('bg-green-500');
        });
    });
});

