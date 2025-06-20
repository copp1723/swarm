// Dark mode utility for theme management
export class DarkModeManager {
    constructor() {
        this.storageKey = 'dark-mode-preference';
        this.init();
    }
    
    init() {
        // Check for saved preference, OS preference, or default to light mode
        const savedTheme = localStorage.getItem(this.storageKey);
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
            this.enableDarkMode();
        } else {
            this.enableLightMode();
        }
        
        // Listen for OS theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(this.storageKey)) {
                if (e.matches) {
                    this.enableDarkMode();
                } else {
                    this.enableLightMode();
                }
            }
        });
        
        // Setup toggle button
        this.setupToggleButton();
    }
    
    enableDarkMode() {
        document.documentElement.classList.add('dark');
        localStorage.setItem(this.storageKey, 'dark');
        this.updateToggleButton();
    }
    
    enableLightMode() {
        document.documentElement.classList.remove('dark');
        localStorage.setItem(this.storageKey, 'light');
        this.updateToggleButton();
    }
    
    toggle() {
        if (this.isDarkMode()) {
            this.enableLightMode();
        } else {
            this.enableDarkMode();
        }
    }
    
    isDarkMode() {
        return document.documentElement.classList.contains('dark');
    }
    
    setupToggleButton() {
        const toggleButton = document.getElementById('dark-mode-toggle');
        if (toggleButton) {
            toggleButton.addEventListener('click', () => this.toggle());
        }
    }
    
    updateToggleButton() {
        const toggleButton = document.getElementById('dark-mode-toggle');
        if (toggleButton) {
            const moonIcon = toggleButton.querySelector('[data-lucide="moon"]');
            const sunIcon = toggleButton.querySelector('[data-lucide="sun"]');
            
            if (this.isDarkMode()) {
                moonIcon?.classList.add('hidden');
                sunIcon?.classList.remove('hidden');
            } else {
                moonIcon?.classList.remove('hidden');
                sunIcon?.classList.add('hidden');
            }
        }
    }
}

// Initialize dark mode manager globally
export const darkModeManager = new DarkModeManager();

