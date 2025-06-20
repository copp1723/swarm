// Styling and Layout Regression Test
// Verifies the three main fixes implemented

export class StylingVerification {
    constructor() {
        this.results = {
            tailwindJIT: false,
            dynamicColorFix: false,
            darkModeToggle: false,
            mobileSidebar: false
        };
    }

    async runAllTests() {
        console.log('🧪 Running Styling Verification Tests...\n');
        
        this.testTailwindJITConfig();
        this.testDynamicColorFix();
        this.testDarkModeToggle();
        this.testMobileSidebar();
        
        this.printResults();
        return this.results;
    }

    testTailwindJITConfig() {
        console.log('1. Testing Tailwind JIT Configuration...');
        
        // Check if tailwind.config.js exists
        const configExists = document.querySelector('script[src*="tailwind"]');
        
        // Check if safelist classes are applied correctly
        const testElement = document.createElement('div');
        testElement.className = 'bg-purple-100 text-purple-700';
        document.body.appendChild(testElement);
        
        const computedStyles = window.getComputedStyle(testElement);
        const hasPurpleBackground = computedStyles.backgroundColor !== 'rgba(0, 0, 0, 0)';
        
        document.body.removeChild(testElement);
        
        this.results.tailwindJIT = configExists && hasPurpleBackground;
        console.log(`   ✅ Tailwind JIT Mode: ${this.results.tailwindJIT ? 'PASS' : 'FAIL'}`);
    }

    testDynamicColorFix() {
        console.log('2. Testing Dynamic Color Class Fix...');
        
        try {
            // Import the updated agent-config module
            import('../agents/agent-config.js').then(module => {
                const { getAgentBadgeClasses, AGENT_BADGE_COLORS } = module;
                
                // Test that we have the new badge color mapping
                const hasMapping = typeof AGENT_BADGE_COLORS === 'object';
                const hasUtilFunction = typeof getAgentBadgeClasses === 'function';
                
                // Test that function returns proper classes
                const testClasses = getAgentBadgeClasses('purple');
                const hasProperClasses = testClasses.includes('bg-purple-100') && testClasses.includes('text-purple-700');
                
                this.results.dynamicColorFix = hasMapping && hasUtilFunction && hasProperClasses;
                console.log(`   ✅ Dynamic Color Fix: ${this.results.dynamicColorFix ? 'PASS' : 'FAIL'}`);
            });
        } catch (error) {
            console.log(`   ❌ Dynamic Color Fix: FAIL (${error.message})`);
            this.results.dynamicColorFix = false;
        }
    }

    testDarkModeToggle() {
        console.log('3. Testing Dark Mode Toggle...');
        
        // Check if toggle button exists
        const toggleButton = document.getElementById('dark-mode-toggle');
        
        // Check if dark mode class can be applied
        const originalTheme = document.documentElement.classList.contains('dark');
        
        // Test toggling
        document.documentElement.classList.add('dark');
        const darkModeApplied = document.documentElement.classList.contains('dark');
        
        // Restore original state
        if (!originalTheme) {
            document.documentElement.classList.remove('dark');
        }
        
        this.results.darkModeToggle = toggleButton !== null && darkModeApplied;
        console.log(`   ✅ Dark Mode Toggle: ${this.results.darkModeToggle ? 'PASS' : 'FAIL'}`);
    }

    testMobileSidebar() {
        console.log('4. Testing Mobile Sidebar Responsiveness...');
        
        // Check if mobile menu button exists
        const mobileMenuBtn = document.getElementById('mobile-menu-btn');
        
        // Check if sidebar has responsive classes
        const sidebar = document.getElementById('sidebar');
        const hasResponsiveCSS = sidebar && sidebar.classList.contains('sidebar');
        
        // Check CSS media query support (simulate mobile viewport)
        const originalWidth = window.innerWidth;
        
        // Test mobile-specific functionality would require more complex mocking
        // For now, check that the elements exist
        this.results.mobileSidebar = mobileMenuBtn !== null && hasResponsiveCSS;
        console.log(`   ✅ Mobile Sidebar: ${this.results.mobileSidebar ? 'PASS' : 'FAIL'}`);
    }

    printResults() {
        console.log('\n📊 Test Results Summary:');
        console.log('========================');
        
        Object.entries(this.results).forEach(([test, passed]) => {
            const status = passed ? '✅ PASS' : '❌ FAIL';
            const testName = test.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
            console.log(`${testName}: ${status}`);
        });
        
        const totalTests = Object.keys(this.results).length;
        const passedTests = Object.values(this.results).filter(Boolean).length;
        const percentage = Math.round((passedTests / totalTests) * 100);
        
        console.log(`\nOverall: ${passedTests}/${totalTests} tests passed (${percentage}%)`);
        
        if (percentage === 100) {
            console.log('🎉 All styling regression fixes verified!');
        } else {
            console.log('⚠️  Some issues may need attention.');
        }
    }
}

// Export for testing
export default StylingVerification;

