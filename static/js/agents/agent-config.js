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

// Pre-mapped color classes for badges and backgrounds to avoid dynamic class generation
export const AGENT_BADGE_COLORS = {
    purple: {
        background: 'bg-purple-100',
        text: 'text-purple-700',
        darkBackground: 'dark:bg-purple-900',
        darkText: 'dark:text-purple-200',
        badge: 'agent-badge-purple'
    },
    green: {
        background: 'bg-green-100',
        text: 'text-green-700',
        darkBackground: 'dark:bg-green-900',
        darkText: 'dark:text-green-200',
        badge: 'agent-badge-green'
    },
    blue: {
        background: 'bg-blue-100',
        text: 'text-blue-700',
        darkBackground: 'dark:bg-blue-900',
        darkText: 'dark:text-blue-200',
        badge: 'agent-badge-blue'
    },
    red: {
        background: 'bg-red-100',
        text: 'text-red-700',
        darkBackground: 'dark:bg-red-900',
        darkText: 'dark:text-red-200',
        badge: 'agent-badge-red'
    },
    orange: {
        background: 'bg-orange-100',
        text: 'text-orange-700',
        darkBackground: 'dark:bg-orange-900',
        darkText: 'dark:text-orange-200',
        badge: 'agent-badge-orange'
    },
    gray: {
        background: 'bg-gray-100',
        text: 'text-gray-700',
        darkBackground: 'dark:bg-gray-900',
        darkText: 'dark:text-gray-200',
        badge: 'agent-badge-gray'
    }
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

// Get badge classes for agent color
export function getAgentBadgeClasses(color) {
    const colorConfig = AGENT_BADGE_COLORS[color] || AGENT_BADGE_COLORS.gray;
    return `${colorConfig.background} ${colorConfig.text} ${colorConfig.darkBackground} ${colorConfig.darkText}`;
}

// Get agent badge component class
export function getAgentBadgeClass(color) {
    const colorConfig = AGENT_BADGE_COLORS[color] || AGENT_BADGE_COLORS.gray;
    return colorConfig.badge;
}
//# sourceMappingURL=agent-config.js.map
