// Custom commands for testing the MCP Agent Chat Interface

// Wait for application to be fully loaded
Cypress.Commands.add('waitForAppReady', () => {
  cy.get('body').should('be.visible')
  cy.get('#sidebar').should('be.visible')
  cy.get('.main-content').should('be.visible')
  cy.window().should('have.property', 'lucide')
  
  // Wait for Lucide icons to render
  cy.get('[data-lucide]').should('exist')
  cy.wait(1000) // Allow time for dynamic content loading
})

// Test sidebar toggle functionality
Cypress.Commands.add('testSidebarToggle', () => {
  // Test desktop sidebar collapse
  cy.get('#collapse-sidebar').should('be.visible').click()
  cy.get('#sidebar').should('have.class', 'collapsed')
  
  // Test sidebar expand
  cy.get('#collapse-sidebar').click()
  cy.get('#sidebar').should('not.have.class', 'collapsed')
  
  // Test mobile menu button (if viewport is mobile)
  cy.viewport(390, 844)
  cy.get('#mobile-menu-btn').should('be.visible').click()
  cy.get('#sidebar').should('be.visible')
  
  // Close mobile menu
  cy.get('#mobile-menu-btn').click()
})

// Test chat functionality
Cypress.Commands.add('testChatSend', () => {
  // First select an agent
  cy.get('#agent-nav-list').should('exist')
  
  // Try to start with Product Agent
  cy.contains('Start with Product Agent').click()
  
  // Wait for chat interface to load
  cy.get('[data-testid="chat-input"], input[type="text"], textarea').should('be.visible')
  
  // Type a test message
  cy.get('[data-testid="chat-input"], input[type="text"], textarea').first()
    .type('Hello, this is a test message{enter}')
  
  // Verify message was sent (look for message in chat)
  cy.contains('Hello, this is a test message').should('be.visible')
})

// Test file upload stub
Cypress.Commands.add('testFileUploadStub', () => {
  // Look for file upload button or input
  cy.get('input[type="file"], [data-testid="file-upload"], button:contains("Upload")').should('exist')
  
  // Create a test file
  const fileName = 'test-file.txt'
  const fileContent = 'This is a test file for upload testing'
  
  // Simulate file selection (this tests the UI, not actual upload)
  cy.get('input[type="file"]').first().selectFile({
    contents: Cypress.Buffer.from(fileContent),
    fileName: fileName,
    mimeType: 'text/plain'
  }, { force: true })
})

// Test collaboration modal
Cypress.Commands.add('testCollaborationModal', () => {
  // Click the multi-agent collaboration button
  cy.get('#open-collab-btn').should('be.visible').click()
  
  // Check if modal opens
  cy.get('#collab-modal').should('not.have.class', 'hidden')
  
  // Look for modal content
  cy.get('#collab-modal').within(() => {
    cy.get('button, [role="button"]').should('exist')
  })
  
  // Close modal (look for close button or click outside)
  cy.get('body').type('{esc}') // Try escape key
})

// Test keyboard shortcuts
Cypress.Commands.add('testKeyboardShortcuts', () => {
  // Test common keyboard shortcuts
  
  // Focus on chat input with Ctrl+/ or Cmd+/
  cy.get('body').type('{cmd}/')
  cy.focused().should('have.attr', 'type', 'text').or('have.prop', 'tagName', 'TEXTAREA')
  
  // Test Escape to close modals
  cy.get('body').type('{esc}')
  
  // Test Tab navigation
  cy.get('body').tab()
  cy.focused().should('be.visible')
  
  // Test Enter to send message
  cy.get('[data-testid="chat-input"], input[type="text"], textarea').first()
    .focus()
    .type('Test shortcut message{enter}')
})

// Test dark mode toggle
Cypress.Commands.add('testDarkModeToggle', () => {
  // Click dark mode toggle
  cy.get('#dark-mode-toggle').should('be.visible').click()
  
  // Check if dark mode is applied
  cy.get('html').should('have.class', 'dark').or('have.attr', 'data-theme', 'dark')
  
  // Toggle back to light mode
  cy.get('#dark-mode-toggle').click()
  cy.get('html').should('not.have.class', 'dark')
})

// Test responsive design
Cypress.Commands.add('testResponsiveDesign', (viewport) => {
  const { width, height } = viewport
  cy.viewport(width, height)
  
  // Check that elements are visible and properly arranged
  cy.get('#sidebar').should('be.visible')
  cy.get('.main-content').should('be.visible')
  
  if (width <= 768) {
    // Mobile specific tests
    cy.get('#mobile-menu-btn').should('be.visible')
  } else {
    // Desktop specific tests
    cy.get('#collapse-sidebar').should('be.visible')
  }
})

// Verify no console errors
Cypress.Commands.add('checkConsoleErrors', () => {
  cy.window().then((win) => {
    // Check for JavaScript errors
    win.addEventListener('error', (e) => {
      cy.log('JavaScript Error:', e.error.message)
      throw new Error(`JavaScript Error: ${e.error.message}`)
    })
    
    // Check for unhandled promise rejections
    win.addEventListener('unhandledrejection', (e) => {
      cy.log('Unhandled Promise Rejection:', e.reason)
      throw new Error(`Unhandled Promise Rejection: ${e.reason}`)
    })
  })
})

