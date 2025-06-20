#!/usr/bin/env node

const { spawn } = require('child_process')
const fs = require('fs')
const path = require('path')

// Configuration
const browsers = ['chrome', 'firefox', 'webkit']
const viewports = {
  desktop: { width: 1440, height: 900 },
  tablet: { width: 1024, height: 768 },
  mobile: { width: 390, height: 844 }
}

const testResults = {
  passed: [],
  failed: [],
  screenshots: [],
  issues: []
}

// GitHub issue creation function
async function createGitHubIssue(title, body, labels) {
  // This would integrate with GitHub API
  console.log(`\n📝 GitHub Issue to Create:`)
  console.log(`Title: ${title}`)
  console.log(`Labels: ${labels.join(', ')}`)
  console.log(`Body: ${body.substring(0, 200)}...`)
  
  // Store issue for later creation
  testResults.issues.push({ title, body, labels })
}

// Run Cypress tests for a specific browser
function runCypressTest(browser) {
  return new Promise((resolve, reject) => {
    console.log(`\n🚀 Running tests in ${browser.toUpperCase()}...`)
    
    const cypressArgs = [
      'run',
      '--browser', browser,
      '--spec', 'cypress/e2e/cross-browser-viewport-qa.cy.js',
      '--reporter', 'json',
      '--reporter-options', `output=cypress/results/${browser}-results.json`
    ]
    
    const cypress = spawn('npx', ['cypress', ...cypressArgs], {
      stdio: 'inherit',
      cwd: process.cwd()
    })
    
    cypress.on('close', (code) => {
      if (code === 0) {
        console.log(`✅ ${browser} tests completed successfully`)
        testResults.passed.push(browser)
      } else {
        console.log(`❌ ${browser} tests failed`)
        testResults.failed.push(browser)
      }
      resolve(code)
    })
    
    cypress.on('error', (error) => {
      console.error(`Error running ${browser} tests:`, error)
      testResults.failed.push(browser)
      reject(error)
    })
  })
}

// Check if the Flask app is running
function checkAppRunning() {
  return new Promise((resolve) => {
    const http = require('http')
    const req = http.get('http://localhost:5000', (res) => {
      resolve(true)
    })
    
    req.on('error', () => {
      resolve(false)
    })
    
    req.setTimeout(5000, () => {
      req.destroy()
      resolve(false)
    })
  })
}

// Start the Flask application
function startApp() {
  return new Promise((resolve, reject) => {
    console.log('🚀 Starting Flask application...')
    
    const app = spawn('python', ['app.py'], {
      cwd: process.cwd(),
      detached: true,
      stdio: 'pipe'
    })
    
    // Wait for app to start
    setTimeout(async () => {
      const isRunning = await checkAppRunning()
      if (isRunning) {
        console.log('✅ Flask app is running on http://localhost:5000')
        resolve(app)
      } else {
        console.log('❌ Failed to start Flask app')
        reject(new Error('Flask app failed to start'))
      }
    }, 5000)
  })
}

// Generate test report
function generateReport() {
  const report = {
    timestamp: new Date().toISOString(),
    browsers: browsers,
    viewports: viewports,
    results: {
      passed: testResults.passed,
      failed: testResults.failed,
      issues: testResults.issues
    },
    summary: {
      totalBrowsers: browsers.length,
      passedBrowsers: testResults.passed.length,
      failedBrowsers: testResults.failed.length,
      issuesCreated: testResults.issues.length
    }
  }
  
  // Save report
  const reportPath = path.join(process.cwd(), 'cypress', 'reports', 'cross-browser-qa-report.json')
  
  // Ensure reports directory exists
  fs.mkdirSync(path.dirname(reportPath), { recursive: true })
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2))
  
  console.log(`\n📊 Test Report saved to: ${reportPath}`)
  return report
}

// Print summary
function printSummary(report) {
  console.log('\n' + '='.repeat(50))
  console.log('🎯 CROSS-BROWSER QA TEST SUMMARY')
  console.log('='.repeat(50))
  
  console.log(`\n📊 Test Results:`)
  console.log(`   Total Browsers Tested: ${report.summary.totalBrowsers}`)
  console.log(`   ✅ Passed: ${report.summary.passedBrowsers}`)
  console.log(`   ❌ Failed: ${report.summary.failedBrowsers}`)
  
  if (report.results.passed.length > 0) {
    console.log(`\n✅ Successful Browsers:`)
    report.results.passed.forEach(browser => {
      console.log(`   - ${browser}`)
    })
  }
  
  if (report.results.failed.length > 0) {
    console.log(`\n❌ Failed Browsers:`)
    report.results.failed.forEach(browser => {
      console.log(`   - ${browser}`)
    })
  }
  
  console.log(`\n🎯 Tested Features:`)
  console.log(`   - Sidebar toggle functionality`)
  console.log(`   - Chat send functionality`) 
  console.log(`   - File upload stub`)
  console.log(`   - Collaboration modal`)
  console.log(`   - Keyboard shortcuts`)
  console.log(`   - Responsive design integrity`)
  
  console.log(`\n📱 Tested Viewports:`)
  Object.entries(viewports).forEach(([name, { width, height }]) => {
    console.log(`   - ${name}: ${width}x${height}`)
  })
  
  if (report.summary.issuesCreated > 0) {
    console.log(`\n🐛 GitHub Issues to Create: ${report.summary.issuesCreated}`)
    report.results.issues.forEach((issue, index) => {
      console.log(`   ${index + 1}. ${issue.title}`)
    })
  }
  
  console.log('\n' + '='.repeat(50))
}

// Main execution function
async function main() {
  try {
    console.log('🎯 Starting Cross-Browser & Viewport QA Testing')
    console.log('Testing browsers:', browsers.join(', '))
    
    // Check if app is already running
    const isAppRunning = await checkAppRunning()
    let appProcess = null
    
    if (!isAppRunning) {
      appProcess = await startApp()
    } else {
      console.log('✅ Flask app is already running')
    }
    
    // Create results directories
    fs.mkdirSync(path.join(process.cwd(), 'cypress', 'results'), { recursive: true })
    fs.mkdirSync(path.join(process.cwd(), 'cypress', 'reports'), { recursive: true })
    
    // Run tests for each browser
    for (const browser of browsers) {
      try {
        await runCypressTest(browser)
        // Add delay between browser tests
        await new Promise(resolve => setTimeout(resolve, 2000))
      } catch (error) {
        console.error(`Failed to run tests for ${browser}:`, error.message)
      }
    }
    
    // Generate and display report
    const report = generateReport()
    printSummary(report)
    
    // Clean up - stop the app if we started it
    if (appProcess) {
      console.log('\n🛑 Stopping Flask application...')
      appProcess.kill()
    }
    
    // Exit with appropriate code
    process.exit(testResults.failed.length === 0 ? 0 : 1)
    
  } catch (error) {
    console.error('❌ Test execution failed:', error.message)
    process.exit(1)
  }
}

// Handle process signals
process.on('SIGINT', () => {
  console.log('\n🛑 Test execution interrupted')
  process.exit(1)
})

process.on('SIGTERM', () => {
  console.log('\n🛑 Test execution terminated')
  process.exit(1)
})

// Run the tests
if (require.main === module) {
  main()
}

module.exports = { main, createGitHubIssue, generateReport }

