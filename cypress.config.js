const { defineConfig } = require('cypress')

module.exports = defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5000',
    supportFile: 'cypress/support/e2e.js',
    specPattern: 'cypress/e2e/**/*.cy.{js,jsx,ts,tsx}',
    viewportWidth: 1440,
    viewportHeight: 900,
    video: true,
    screenshotOnRunFailure: true,
    screenshotsFolder: 'cypress/screenshots',
    videosFolder: 'cypress/videos',
    defaultCommandTimeout: 10000,
    requestTimeout: 10000,
    responseTimeout: 10000,
    pageLoadTimeout: 30000,
    setupNodeEvents(on, config) {
      // implement node event listeners here
      on('before:browser:launch', (browser = {}, launchOptions) => {
        if (browser.name === 'chrome') {
          launchOptions.args.push('--disable-dev-shm-usage')
          launchOptions.args.push('--no-sandbox')
          launchOptions.args.push('--disable-gpu')
        }
        
        if (browser.name === 'firefox') {
          launchOptions.preferences['dom.serviceWorkers.enabled'] = false
        }
        
        return launchOptions
      })
      
      // Task for creating GitHub issues with screenshots
      on('task', {
        createGitHubIssue({ title, body, labels, screenshotPath }) {
          return new Promise((resolve, reject) => {
            // This will be used to create GitHub issues via API
            console.log('GitHub Issue to create:', { title, body, labels, screenshotPath })
            resolve({ success: true, issueUrl: 'https://github.com/placeholder/issues/new' })
          })
        }
      })
    },
  },
  
  // Define multiple viewport configurations for responsive testing
  env: {
    viewports: {
      desktop: { width: 1440, height: 900 },
      tablet: { width: 1024, height: 768 },
      mobile: { width: 390, height: 844 }
    },
    browsers: ['chrome', 'firefox', 'webkit']
  }
})

