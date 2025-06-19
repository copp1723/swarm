// Agent configuration module
export const AGENTS = [
    { 
        id: 'product_01', 
        name: 'Product Agent', 
        role: 'Product management and feature planning', 
        icon: 'package', 
        color: 'purple' 
    },
    { 
        id: 'coding_01', 
        name: 'Coding Agent', 
        role: 'Software development and code implementation', 
        icon: 'code', 
        color: 'green' 
    },
    { 
        id: 'bug_01', 
        name: 'Bug Agent', 
        role: 'Bug detection and quality assurance', 
        icon: 'bug', 
        color: 'red' 
    },
    { 
        id: 'general_01', 
        name: 'General Assistant', 
        role: 'General purpose AI assistant', 
        icon: 'message-circle', 
        color: 'gray' 
    }
];

export const AGENT_COLORS = {
    purple: 'bg-purple-500',
    green: 'bg-green-500',
    blue: 'bg-blue-500',
    red: 'bg-red-500',
    orange: 'bg-orange-500',
    gray: 'bg-gray-500'
};

export function getAgentById(agentId) {
    return AGENTS.find(a => a.id === agentId);
}

export function getAgentByName(agentName) {
    return AGENTS.find(a => 
        a.name === agentName || 
        a.name.toLowerCase().includes(agentName.toLowerCase()) ||
        a.id.includes(agentName)
    );
}

export function getAgentColor(color) {
    return AGENT_COLORS[color] || AGENT_COLORS.gray;
}