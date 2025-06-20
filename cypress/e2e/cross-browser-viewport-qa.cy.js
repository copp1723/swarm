describe('Cross-Browser & Viewport QA Suite', () => {
  const viewports = {
    desktop: { width: 1440, height: 900 },
    tablet: { width: 1024, height: 768 },
    mobile: { width: 390, height: 844 }
  }
  
  const testResults = {
    failures: [],
    passed: []
  }

  beforeEach(() => {
    cy.visit('/')
    cy.waitForAppReady()
  })

  // Test suite for each viewport
  Object.entries(viewports).forEach(([viewportName, { width, height }]) => {
    context(`${viewportName.toUpperCase()} Viewport (${width}x${height})`, () => {
      beforeEach(() => {
        cy.viewport(width, height)
        cy.wait(500) // Allow layout to adjust
      })

      it('should load the application correctly', () => {
        cy.get('body').should('be.visible')
        cy.get('#sidebar').should('be.visible')
        cy.get('.main-content').should('be.visible')
        cy.get('[data-lucide]').should('exist')
        
        // Take screenshot for verification
        cy.screenshotWithContext(`app-load-${viewportName}`)
        
        cy.then(() => {
          testResults.passed.push(`App load - ${viewportName}`)
        })
      })

      it('should handle sidebar toggle correctly', () => {
        cy.then(() => {
          try {
            if (width <= 768) {
              // Mobile sidebar test
              cy.get('#mobile-menu-btn').should('be.visible')
              cy.get('#mobile-menu-btn').click()
              cy.wait(300)
              
              // Check if sidebar is accessible
              cy.get('#sidebar').should('be.visible')
              cy.screenshotWithContext(`sidebar-mobile-open-${viewportName}`)
              
              // Close mobile menu
              cy.get('#mobile-menu-btn').click()
              cy.wait(300)
              
            } else {
              // Desktop sidebar test
              cy.get('#collapse-sidebar').should('be.visible')
              cy.get('#collapse-sidebar').click()
              cy.wait(300)
              
              // Verify sidebar collapsed state
              cy.get('#sidebar').then($sidebar => {
                const hasCollapsed = $sidebar.hasClass('collapsed') || 
                                   $sidebar.css('transform').includes('translateX') ||
                                   $sidebar.width() < 200
                
                if (!hasCollapsed) {
                  cy.screenshotWithContext(`sidebar-collapse-issue-${viewportName}`)
                  testResults.failures.push({
                    test: 'Sidebar Toggle',
                    viewport: viewportName,
                    browser: Cypress.browser.name,
                    issue: 'Sidebar did not collapse properly',
                    screenshot: `sidebar-collapse-issue-${viewportName}`
                  })
                }
              })
              
              // Expand sidebar again
              cy.get('#collapse-sidebar').click()
              cy.wait(300)
            }
            
            cy.screenshotWithContext(`sidebar-toggle-${viewportName}`)
            testResults.passed.push(`Sidebar toggle - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`sidebar-error-${viewportName}`)
            testResults.failures.push({
              test: 'Sidebar Toggle',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: error.message,
              screenshot: `sidebar-error-${viewportName}`
            })
          }
        })
      })

      it('should handle chat send functionality', () => {
        cy.then(() => {
          try {
            // Click to start with Product Agent
            cy.contains('Start with Product Agent').should('be.visible').click()
            cy.wait(1000)
            
            // Look for chat input field
            cy.get('input[type="text"], textarea, [contenteditable="true"]')
              .filter(':visible')
              .first()
              .as('chatInput')
            
            cy.get('@chatInput').should('be.visible')
            
            // Type test message
            const testMessage = `Test message from ${viewportName} viewport`
            cy.get('@chatInput').clear().type(testMessage)
            
            // Try to send message (Enter key or send button)
            cy.get('@chatInput').type('{enter}')
            
            // Alternative: look for send button
            cy.get('button').contains(/send|submit/i).then($btn => {
              if ($btn.length > 0 && $btn.is(':visible')) {
                cy.wrap($btn).click()
              }
            })
            
            cy.wait(1000)
            cy.screenshotWithContext(`chat-send-${viewportName}`)
            testResults.passed.push(`Chat send - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`chat-send-error-${viewportName}`)
            testResults.failures.push({
              test: 'Chat Send',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: `Chat send failed: ${error.message}`,
              screenshot: `chat-send-error-${viewportName}`
            })
          }
        })
      })

      it('should handle file upload stub', () => {
        cy.then(() => {
          try {
            // Look for file upload elements
            cy.get('input[type="file"], [data-testid*="upload"], button').contains(/upload|file/i)
              .should('exist')
              .first()
              .as('uploadElement')
            
            // If it's a file input, test file selection
            cy.get('@uploadElement').then($el => {
              if ($el.is('input[type="file"]')) {
                const fileName = 'test-document.txt'
                const fileContent = 'Test file content for upload testing'
                
                cy.get('@uploadElement').selectFile({
                  contents: Cypress.Buffer.from(fileContent),
                  fileName: fileName,
                  mimeType: 'text/plain'
                }, { force: true })
              } else {
                // If it's a button, just verify it's clickable
                cy.get('@uploadElement').should('be.visible').and('not.be.disabled')
              }
            })
            
            cy.screenshotWithContext(`file-upload-${viewportName}`)
            testResults.passed.push(`File upload stub - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`file-upload-error-${viewportName}`)
            testResults.failures.push({
              test: 'File Upload Stub',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: `File upload test failed: ${error.message}`,
              screenshot: `file-upload-error-${viewportName}`
            })
          }
        })
      })

      it('should handle collaboration modal', () => {
        cy.then(() => {
          try {
            // Click the multi-agent collaboration button
            cy.get('#open-collab-btn').should('be.visible').click()
            cy.wait(500)
            
            // Check if modal appears
            cy.get('#collab-modal, [role="dialog"], .modal').should('be.visible')
            cy.screenshotWithContext(`collab-modal-open-${viewportName}`)
            
            // Try to close modal with Escape key
            cy.get('body').type('{esc}')
            cy.wait(300)
            
            // Alternative: look for close button
            cy.get('button[aria-label*="close"], button').contains(/close|cancel/i).then($btn => {
              if ($btn.length > 0 && $btn.is(':visible')) {
                cy.wrap($btn).click()
              }
            })
            
            cy.screenshotWithContext(`collab-modal-${viewportName}`)
            testResults.passed.push(`Collaboration modal - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`collab-modal-error-${viewportName}`)
            testResults.failures.push({
              test: 'Collaboration Modal',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: `Collaboration modal failed: ${error.message}`,
              screenshot: `collab-modal-error-${viewportName}`
            })
          }
        })
      })

      it('should handle keyboard shortcuts', () => {
        cy.then(() => {
          try {
            // Test Tab navigation
            cy.get('body').tab()
            cy.focused().should('be.visible')
            
            // Test Escape key
            cy.get('body').type('{esc}')
            
            // Test Enter key for form submission
            cy.get('input[type="text"], textarea').first().then($input => {
              if ($input.length > 0) {
                cy.wrap($input).focus().type('Test keyboard shortcuts{enter}')
              }
            })
            
            cy.screenshotWithContext(`keyboard-shortcuts-${viewportName}`)
            testResults.passed.push(`Keyboard shortcuts - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`keyboard-shortcuts-error-${viewportName}`)
            testResults.failures.push({
              test: 'Keyboard Shortcuts',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: `Keyboard shortcuts failed: ${error.message}`,
              screenshot: `keyboard-shortcuts-error-${viewportName}`
            })
          }
        })
      })

      it('should maintain responsive design integrity', () => {
        cy.then(() => {
          try {
            // Check that all critical elements are visible and properly positioned
            cy.get('#sidebar').should('be.visible')
            cy.get('.main-content').should('be.visible')
            cy.get('header').should('be.visible')
            
            // Check for horizontal scrollbars (usually indicate layout issues)
            cy.get('body').then($body => {
              const hasHorizontalScroll = $body[0].scrollWidth > $body[0].clientWidth
              if (hasHorizontalScroll && width >= 390) {
                testResults.failures.push({
                  test: 'Responsive Design',
                  viewport: viewportName,
                  browser: Cypress.browser.name,
                  issue: 'Horizontal scrollbar detected - layout overflow',
                  screenshot: `responsive-overflow-${viewportName}`
                })
              }
            })
            
            // Verify text is readable (not too small)
            cy.get('body').then($body => {
              const fontSize = parseFloat($body.css('font-size'))
              if (fontSize < 14 && width <= 390) {
                testResults.failures.push({
                  test: 'Responsive Design',
                  viewport: viewportName,
                  browser: Cypress.browser.name,
                  issue: `Font size too small on mobile: ${fontSize}px`,
                  screenshot: `responsive-font-${viewportName}`
                })
              }
            })
            
            cy.screenshotWithContext(`responsive-design-${viewportName}`)
            testResults.passed.push(`Responsive design - ${viewportName}`)
            
          } catch (error) {
            cy.screenshotWithContext(`responsive-error-${viewportName}`)
            testResults.failures.push({
              test: 'Responsive Design',
              viewport: viewportName,
              browser: Cypress.browser.name,
              issue: `Responsive design check failed: ${error.message}`,
              screenshot: `responsive-error-${viewportName}`
            })
          }
        })
      })
    })
  })

  // Create GitHub issues for failures after all tests
  after(() => {
    cy.then(() => {
      if (testResults.failures.length > 0) {
        testResults.failures.forEach(failure => {
          const title = `${failure.test} Issue on ${failure.viewport} viewport`
          const description = `
**Issue:** ${failure.issue}
**Browser:** ${failure.browser}
**Viewport:** ${failure.viewport}
**Screenshot:** ${failure.screenshot}

This issue was automatically detected during cross-browser and viewport QA testing.
          `
          
          cy.createGitHubIssue(title, description, ['bug', 'responsive', 'cross-browser'])
        })
        
        cy.log(`Created ${testResults.failures.length} GitHub issues for detected problems`)
      }
      
      cy.log(`QA Summary: ${testResults.passed.length} passed, ${testResults.failures.length} failed`)
    })
  })
})

