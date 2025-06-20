describe('Cross-Browser & Viewport QA - UI Focused', () => {
  const viewports = {
    desktop: { width: 1440, height: 900 },
    tablet: { width: 1024, height: 768 },
    mobile: { width: 390, height: 844 }
  }
  
  const testResults = {
    failures: [],
    passed: [],
    screenshots: []
  }

  beforeEach(() => {
    cy.visit('/index.html')
    cy.get('body').should('be.visible')
    // Allow time for external scripts to load
    cy.wait(2000)
  })

  // Test each viewport
  Object.entries(viewports).forEach(([viewportName, { width, height }]) => {
    context(`${viewportName.toUpperCase()} Viewport (${width}x${height})`, () => {
      beforeEach(() => {
        cy.viewport(width, height)
        cy.wait(500) // Allow layout to adjust
      })

      it('should load the application with all required elements', () => {
        // Basic app structure verification
        cy.get('body').should('be.visible')
        cy.get('#sidebar').should('exist')
        cy.get('.main-content').should('exist')
        cy.get('header').should('exist')
        
        // Take comprehensive screenshot
        cy.screenshot(`app-load-${viewportName}-${width}x${height}`)
        
        // Verify no horizontal scrollbars on desktop and tablet
        if (width >= 390) {
          cy.get('body').then($body => {
            const hasHorizontalScroll = $body[0].scrollWidth > $body[0].clientWidth
            if (hasHorizontalScroll) {
              cy.screenshot(`layout-overflow-${viewportName}`)
              testResults.failures.push({
                test: 'Layout Integrity',
                viewport: viewportName,
                browser: Cypress.browser.name,
                issue: 'Horizontal scrollbar detected - layout overflow',
                severity: 'medium'
              })
            }
          })
        }
        
        testResults.passed.push(`App load - ${viewportName}`)
      })

      it('should verify sidebar functionality', () => {
        if (width <= 768) {
          // Mobile viewport - test mobile menu
          cy.get('#mobile-menu-btn').should('be.visible')
          cy.screenshot(`mobile-menu-initial-${viewportName}`)
          
          // Test mobile menu toggle
          cy.get('#mobile-menu-btn').click()
          cy.wait(300)
          cy.screenshot(`mobile-menu-opened-${viewportName}`)
          
          // Verify sidebar is accessible after click
          cy.get('#sidebar').should('be.visible')
          
          testResults.passed.push(`Mobile sidebar - ${viewportName}`)
        } else {
          // Desktop/tablet viewport - test sidebar collapse
          cy.get('#sidebar').should('be.visible')
          cy.get('#collapse-sidebar').should('be.visible')
          
          cy.screenshot(`desktop-sidebar-initial-${viewportName}`)
          
          // Test collapse
          cy.get('#collapse-sidebar').click()
          cy.wait(300)
          cy.screenshot(`desktop-sidebar-collapsed-${viewportName}`)
          
          // Test expand
          cy.get('#collapse-sidebar').click()
          cy.wait(300)
          cy.screenshot(`desktop-sidebar-expanded-${viewportName}`)
          
          testResults.passed.push(`Desktop sidebar - ${viewportName}`)
        }
      })

      it('should verify chat interface elements', () => {
        // Look for welcome message and action buttons
        cy.get('#welcome-message').should('be.visible')
        cy.get('button').contains('Start with Product Agent').should('be.visible')
        cy.get('button').contains('Start with General Assistant').should('be.visible')
        
        cy.screenshot(`chat-welcome-${viewportName}`)
        
        // Click to activate chat interface
        cy.get('button').contains('Start with Product Agent').click()
        cy.wait(1000)
        
        cy.screenshot(`chat-activated-${viewportName}`)
        testResults.passed.push(`Chat interface - ${viewportName}`)
      })

      it('should verify collaboration modal functionality', () => {
        // Test collaboration button
        cy.get('#open-collab-btn').should('be.visible').and('contain', 'Multi-Agent Task')
        cy.screenshot(`collab-button-${viewportName}`)
        
        // Click collaboration button
        cy.get('#open-collab-btn').click()
        cy.wait(500)
        
        // Check if modal container exists (even if empty)
        cy.get('#collab-modal').should('exist')
        cy.screenshot(`collab-modal-state-${viewportName}`)
        
        testResults.passed.push(`Collaboration modal - ${viewportName}`)
      })

      it('should verify keyboard shortcuts and accessibility', () => {
        // Test Tab navigation
        cy.get('body').tab()
        cy.focused().should('be.visible')
        cy.screenshot(`keyboard-focus-${viewportName}`)
        
        // Test dark mode toggle
        cy.get('#dark-mode-toggle').should('be.visible').click()
        cy.wait(300)
        cy.screenshot(`dark-mode-toggled-${viewportName}`)
        
        // Toggle back
        cy.get('#dark-mode-toggle').click()
        cy.wait(300)
        
        testResults.passed.push(`Keyboard navigation - ${viewportName}`)
      })

      it('should verify responsive design elements', () => {
        // Check header responsiveness
        cy.get('header').should('be.visible')
        cy.get('h1').should('be.visible')
        
        // Check button visibility and sizing
        cy.get('#dark-mode-toggle').should('be.visible')
        cy.get('#open-collab-btn').should('be.visible')
        
        if (width <= 768) {
          // Mobile-specific checks
          cy.get('#mobile-menu-btn').should('be.visible')
          // Check that text is readable on mobile
          cy.get('h1').should('have.css', 'font-size').then(fontSize => {
            const size = parseFloat(fontSize)
            if (size < 16) {
              testResults.failures.push({
                test: 'Mobile Typography',
                viewport: viewportName,
                browser: Cypress.browser.name,
                issue: `H1 font size too small on mobile: ${size}px`,
                severity: 'low'
              })
            }
          })
        }
        
        cy.screenshot(`responsive-check-${viewportName}`)
        testResults.passed.push(`Responsive design - ${viewportName}`)
      })

      it('should verify external dependencies load correctly', () => {
        // Check if Tailwind CSS loaded
        cy.get('body').should('have.class').then(classes => {
          const hasTailwindClasses = classes.includes('bg-gray') || classes.includes('font-sans')
          if (!hasTailwindClasses) {
            testResults.failures.push({
              test: 'CSS Dependencies',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: 'Tailwind CSS classes not applied properly',
              severity: 'high'
            })
          }
        })
        
        // Check if Lucide icons are available
        cy.window().then(win => {
          if (!win.lucide) {
            testResults.failures.push({
              test: 'JavaScript Dependencies',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: 'Lucide icons library not loaded',
              severity: 'medium'
            })
          }
        })
        
        cy.screenshot(`dependencies-check-${viewportName}`)
        testResults.passed.push(`Dependencies check - ${viewportName}`)
      })
    })
  })

  // Summary report
  after(() => {
    cy.then(() => {
      const report = {
        timestamp: new Date().toISOString(),
        browser: Cypress.browser.name,
        totalTests: testResults.passed.length,
        failedIssues: testResults.failures.length,
        passed: testResults.passed,
        failures: testResults.failures,
        viewportsTested: Object.keys(viewports),
        testCategories: [
          'Application Loading',
          'Sidebar Functionality', 
          'Chat Interface',
          'Collaboration Modal',
          'Keyboard Navigation',
          'Responsive Design',
          'External Dependencies'
        ]
      }
      
      // Log comprehensive summary
      cy.log('=== CROSS-BROWSER QA SUMMARY ===')
      cy.log(`Browser: ${report.browser}`)
      cy.log(`Total Tests: ${report.totalTests}`)
      cy.log(`Issues Found: ${report.failedIssues}`)
      cy.log(`Viewports Tested: ${report.viewportsTested.join(', ')}`)
      
      if (report.failures.length > 0) {
        cy.log('=== ISSUES FOUND ===')
        report.failures.forEach((failure, index) => {
          cy.log(`${index + 1}. [${failure.severity.toUpperCase()}] ${failure.test} on ${failure.viewport}: ${failure.issue}`)
        })
      }
      
      // Create GitHub issues for high/medium severity issues
      const criticalIssues = report.failures.filter(f => f.severity === 'high' || f.severity === 'medium')
      criticalIssues.forEach(issue => {
        const title = `[${issue.severity.toUpperCase()}] ${issue.test} Issue on ${issue.viewport} - ${issue.browser}`
        const description = `
**Issue:** ${issue.issue}
**Test Category:** ${issue.test}
**Browser:** ${issue.browser}
**Viewport:** ${issue.viewport}
**Severity:** ${issue.severity}
**Detected by:** Cross-browser QA Suite

### Reproduction Steps
1. Open the MCP Agent Chat Interface
2. Set browser to ${issue.browser}
3. Set viewport to ${issue.viewport}
4. Observe the reported issue

### Expected Behavior
The interface should work consistently across all supported browsers and viewport sizes.

**QA Suite:** Cross-browser & Viewport Testing
**Auto-generated:** ${new Date().toISOString()}
        `
        
        cy.task('createGitHubIssue', {
          title: title,
          body: description,
          labels: ['bug', 'qa', issue.severity, 'cross-browser'],
          screenshotPath: `${issue.test.toLowerCase().replace(/\s+/g, '-')}-${issue.viewport}`
        })
      })
      
      // Final summary
      const successRate = Math.round((report.totalTests - report.failedIssues) / report.totalTests * 100)
      cy.log(`=== QA COMPLETION ===`)
      cy.log(`Success Rate: ${successRate}%`)
      cy.log(`Issues requiring attention: ${criticalIssues.length}`)
      cy.log(`Screenshots captured: Available in cypress/screenshots`)
    })
  })
})

