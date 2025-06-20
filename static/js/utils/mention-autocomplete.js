/**
 * @ Mention Autocomplete for Agent References
 */

class MentionAutocomplete {
    constructor() {
        this.agents = new Map();
        this.currentInput = null;
        this.dropdown = null;
        this.selectedIndex = -1;
        this.init();
    }

    init() {
        this.createDropdownElement();
        this.setupGlobalEventListeners();
    }

    /**
     * Create the dropdown element
     */
    createDropdownElement() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'mention-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            min-width: 200px;
        `;
        document.body.appendChild(this.dropdown);
    }

    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Hide dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.dropdown.contains(e.target) && e.target !== this.currentInput) {
                this.hideDropdown();
            }
        });

        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isVisible()) {
                this.hideDropdown();
            }
        });
    }

    /**
     * Register agents for autocomplete
     * @param {Array} agentList - Array of agent objects
     */
    registerAgents(agentList) {
        this.agents.clear();
        agentList.forEach(agent => {
            this.agents.set(agent.role, {
                id: agent.role,
                name: agent.name,
                description: agent.description,
                specialties: agent.specialties || []
            });
        });
    }

    /**
     * Enable autocomplete on an input element
     * @param {HTMLInputElement|HTMLTextAreaElement} inputElement 
     */
    enableFor(inputElement) {
        inputElement.addEventListener('input', (e) => {
            this.handleInput(e, inputElement);
        });

        inputElement.addEventListener('keydown', (e) => {
            if (this.isVisible()) {
                this.handleKeyNavigation(e, inputElement);
            }
        });

        inputElement.addEventListener('blur', (e) => {
            // Delay hiding to allow click on dropdown
            setTimeout(() => {
                if (document.activeElement !== inputElement) {
                    this.hideDropdown();
                }
            }, 150);
        });
    }

    /**
     * Handle input changes
     * @param {Event} e 
     * @param {HTMLElement} inputElement 
     */
    handleInput(e, inputElement) {
        const value = inputElement.value;
        const cursorPosition = inputElement.selectionStart;
        
        // Find @ symbol before cursor
        const textBeforeCursor = value.substring(0, cursorPosition);
        const mentionMatch = textBeforeCursor.match(/@([a-zA-Z0-9_]*)$/);
        
        if (mentionMatch) {
            this.currentInput = inputElement;
            const query = mentionMatch[1].toLowerCase();
            const matches = this.findMatches(query);
            
            if (matches.length > 0) {
                this.showDropdown(inputElement, mentionMatch.index, matches);
            } else {
                this.hideDropdown();
            }
        } else {
            this.hideDropdown();
        }
    }

    /**
     * Find matching agents
     * @param {string} query 
     * @returns {Array}
     */
    findMatches(query) {
        const matches = [];
        
        for (const [id, agent] of this.agents) {
            const nameMatch = agent.name.toLowerCase().includes(query);
            const idMatch = agent.id.toLowerCase().includes(query);
            const specialtyMatch = agent.specialties.some(s => 
                s.toLowerCase().includes(query)
            );
            
            if (nameMatch || idMatch || specialtyMatch || query === '') {
                matches.push({
                    ...agent,
                    score: this.calculateScore(agent, query)
                });
            }
        }
        
        // Sort by relevance score
        return matches.sort((a, b) => b.score - a.score);
    }

    /**
     * Calculate relevance score
     * @param {Object} agent 
     * @param {string} query 
     * @returns {number}
     */
    calculateScore(agent, query) {
        if (query === '') return 50;
        
        let score = 0;
        const lowerQuery = query.toLowerCase();
        
        // Exact name match gets highest score
        if (agent.name.toLowerCase() === lowerQuery) score += 100;
        else if (agent.name.toLowerCase().startsWith(lowerQuery)) score += 80;
        else if (agent.name.toLowerCase().includes(lowerQuery)) score += 60;
        
        // ID matches
        if (agent.id.toLowerCase() === lowerQuery) score += 90;
        else if (agent.id.toLowerCase().startsWith(lowerQuery)) score += 70;
        else if (agent.id.toLowerCase().includes(lowerQuery)) score += 50;
        
        // Specialty matches
        agent.specialties.forEach(specialty => {
            if (specialty.toLowerCase().includes(lowerQuery)) {
                score += 40;
            }
        });
        
        return score;
    }

    /**
     * Show the dropdown
     * @param {HTMLElement} inputElement 
     * @param {number} mentionStartIndex 
     * @param {Array} matches 
     */
    showDropdown(inputElement, mentionStartIndex, matches) {
        this.populateDropdown(matches);
        this.positionDropdown(inputElement, mentionStartIndex);
        this.dropdown.style.display = 'block';
        this.selectedIndex = -1;
    }

    /**
     * Populate dropdown with matches
     * @param {Array} matches 
     */
    populateDropdown(matches) {
        this.dropdown.innerHTML = '';
        
        matches.forEach((agent, index) => {
            const item = document.createElement('div');
            item.className = 'mention-item';
            item.style.cssText = `
                padding: 12px 16px;
                cursor: pointer;
                border-bottom: 1px solid #f1f5f9;
                transition: background-color 0.15s;
            `;
            
            item.innerHTML = `
                <div style="display: flex; align-items: center;">
                    <div style="
                        width: 32px; 
                        height: 32px; 
                        border-radius: 50%; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        display: flex; 
                        align-items: center; 
                        justify-content: center; 
                        color: white; 
                        font-weight: 500;
                        margin-right: 12px;
                    ">
                        ${agent.name.charAt(0).toUpperCase()}
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 500; color: #1e293b;">${agent.name}</div>
                        <div style="font-size: 12px; color: #64748b; margin-top: 2px;">
                            @${agent.id} • ${agent.specialties.join(', ')}
                        </div>
                    </div>
                </div>
            `;
            
            // Hover effects
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
            
            item.addEventListener('click', () => {
                this.selectAgent(agent);
            });
            
            this.dropdown.appendChild(item);
        });
    }

    /**
     * Position dropdown relative to input
     * @param {HTMLElement} inputElement 
     * @param {number} mentionStartIndex 
     */
    positionDropdown(inputElement, mentionStartIndex) {
        const rect = inputElement.getBoundingClientRect();
        
        // Try to position near the @ symbol
        let left = rect.left;
        let top = rect.bottom + 4;
        
        // Adjust if dropdown would go off screen
        const dropdownRect = this.dropdown.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        if (left + 200 > viewportWidth) {
            left = viewportWidth - 220;
        }
        
        if (top + 200 > viewportHeight) {
            top = rect.top - 200 - 4;
        }
        
        this.dropdown.style.left = `${left}px`;
        this.dropdown.style.top = `${top}px`;
    }

    /**
     * Handle keyboard navigation
     * @param {KeyboardEvent} e 
     * @param {HTMLElement} inputElement 
     */
    handleKeyNavigation(e, inputElement) {
        const items = this.dropdown.querySelectorAll('.mention-item');
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.updateSelection();
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.updateSelection();
                break;
                
            case 'Enter':
            case 'Tab':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    const agentId = this.getAgentIdFromItem(items[this.selectedIndex]);
                    const agent = this.agents.get(agentId);
                    if (agent) {
                        this.selectAgent(agent);
                    }
                }
                break;
        }
    }

    /**
     * Update visual selection
     */
    updateSelection() {
        const items = this.dropdown.querySelectorAll('.mention-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.style.backgroundColor = '#f1f5f9';
            } else {
                item.style.backgroundColor = 'white';
            }
        });
    }

    /**
     * Get agent ID from dropdown item
     * @param {HTMLElement} item 
     * @returns {string}
     */
    getAgentIdFromItem(item) {
        const idText = item.querySelector('div div div:last-child').textContent;
        return idText.split(' •')[0].substring(1); // Remove @ symbol
    }

    /**
     * Select an agent and insert into input
     * @param {Object} agent 
     */
    selectAgent(agent) {
        if (!this.currentInput) return;
        
        const value = this.currentInput.value;
        const cursorPosition = this.currentInput.selectionStart;
        const textBeforeCursor = value.substring(0, cursorPosition);
        const textAfterCursor = value.substring(cursorPosition);
        
        // Find the @ symbol
        const mentionMatch = textBeforeCursor.match(/@[a-zA-Z0-9_]*$/);
        if (!mentionMatch) return;
        
        const beforeMention = textBeforeCursor.substring(0, mentionMatch.index);
        const newValue = beforeMention + `@${agent.id} ` + textAfterCursor;
        
        this.currentInput.value = newValue;
        
        // Set cursor after the mention
        const newCursorPos = beforeMention.length + agent.id.length + 2;
        this.currentInput.setSelectionRange(newCursorPos, newCursorPos);
        
        // Trigger input event for other listeners
        this.currentInput.dispatchEvent(new Event('input', { bubbles: true }));
        
        this.hideDropdown();
        this.currentInput.focus();
    }

    /**
     * Hide the dropdown
     */
    hideDropdown() {
        this.dropdown.style.display = 'none';
        this.currentInput = null;
        this.selectedIndex = -1;
    }

    /**
     * Check if dropdown is visible
     * @returns {boolean}
     */
    isVisible() {
        return this.dropdown.style.display === 'block';
    }
}

// Export singleton instance
export const mentionAutocomplete = new MentionAutocomplete();
export default mentionAutocomplete;

