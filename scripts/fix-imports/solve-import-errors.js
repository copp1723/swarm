#!/usr/bin/env node

/**
 * Comprehensive solution for fixing path alias import errors
 * This script provides multiple strategies to resolve import issues
 */

const fs = require('fs').promises;
const path = require('path');

// ANSI color codes for output
const colors = {
    reset: '\x1b[0m',
    bright: '\x1b[1m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    cyan: '\x1b[36m'
};

const log = {
    info: (msg) => console.log(`${colors.blue}ℹ${colors.reset}  ${msg}`),
    success: (msg) => console.log(`${colors.green}✓${colors.reset}  ${msg}`),
    warning: (msg) => console.log(`${colors.yellow}⚠${colors.reset}  ${msg}`),
    error: (msg) => console.log(`${colors.red}✗${colors.reset}  ${msg}`),
    header: (msg) => console.log(`\n${colors.bright}${colors.cyan}${msg}${colors.reset}\n`)
};

/**
 * Strategy 1: Remove all path aliases and use relative imports
 */
async function strategyRelativeOnly() {
    log.header('Strategy 1: Convert all imports to relative paths');
    
    try {
        // Run the fix-imports script
        const { spawn } = require('child_process');
        const fixProcess = spawn('node', [path.join(__dirname, 'fix-imports.js')], {
            stdio: 'inherit'
        });
        
        await new Promise((resolve, reject) => {
            fixProcess.on('close', (code) => {
                if (code === 0) resolve();
                else reject(new Error(`Fix imports failed with code ${code}`));
            });
        });
        
        log.success('All imports converted to relative paths');
    } catch (error) {
        log.error(`Failed to fix imports: ${error.message}`);
        throw error;
    }
}

/**
 * Strategy 2: Add webpack/build tool configuration for path aliases
 */
async function strategyConfigureAliases() {
    log.header('Strategy 2: Configure build tools for path aliases');
    
    // Create webpack config if it doesn't exist
    const webpackConfig = `const path = require('path');

module.exports = {
    resolve: {
        alias: {
            '@': path.resolve(__dirname, 'static/js'),
            '@components': path.resolve(__dirname, 'static/js/components'),
            '@services': path.resolve(__dirname, 'static/js/services'),
            '@utils': path.resolve(__dirname, 'static/js/utils'),
            '@agents': path.resolve(__dirname, 'static/js/agents'),
            '~': path.resolve(__dirname, 'static/js')
        },
        extensions: ['.js', '.jsx', '.ts', '.tsx', '.json']
    }
};`;

    const webpackPath = path.join(__dirname, '../../webpack.config.js');
    
    try {
        await fs.writeFile(webpackPath, webpackConfig);
        log.success('Created webpack configuration with path aliases');
    } catch (error) {
        log.error(`Failed to create webpack config: ${error.message}`);
    }
    
    // Create jsconfig for VS Code
    const jsConfig = {
        "compilerOptions": {
            "baseUrl": "./static",
            "paths": {
                "@/*": ["js/*"],
                "@components/*": ["js/components/*"],
                "@services/*": ["js/services/*"],
                "@utils/*": ["js/utils/*"],
                "@agents/*": ["js/agents/*"],
                "~/*": ["js/*"]
            }
        },
        "exclude": ["node_modules", "dist", "build"]
    };
    
    const jsConfigPath = path.join(__dirname, '../../jsconfig.json');
    
    try {
        await fs.writeFile(jsConfigPath, JSON.stringify(jsConfig, null, 2));
        log.success('Created jsconfig.json for IDE support');
    } catch (error) {
        log.error(`Failed to create jsconfig: ${error.message}`);
    }
}

/**
 * Strategy 3: Create import map for browser ES modules
 */
async function strategyCreateImportMap() {
    log.header('Strategy 3: Create import map for browser ES modules');
    
    const importMap = {
        "imports": {
            "@/": "/static/js/",
            "@components/": "/static/js/components/",
            "@services/": "/static/js/services/",
            "@utils/": "/static/js/utils/",
            "@agents/": "/static/js/agents/",
            "~/": "/static/js/"
        }
    };
    
    const importMapScript = `<!-- Add this to your HTML head section -->
<script type="importmap">
${JSON.stringify(importMap, null, 2)}
</script>`;
    
    const importMapPath = path.join(__dirname, 'import-map.html');
    
    try {
        await fs.writeFile(importMapPath, importMapScript);
        log.success(`Created import map snippet at ${importMapPath}`);
        log.info('Add this to your HTML files to support path aliases in browsers');
    } catch (error) {
        log.error(`Failed to create import map: ${error.message}`);
    }
}

/**
 * Analyze current state
 */
async function analyzeCurrentState() {
    log.header('Analyzing current import state...');
    
    try {
        const { spawn } = require('child_process');
        const analyzeProcess = spawn('node', [path.join(__dirname, 'analyze-imports.js')], {
            stdio: 'inherit'
        });
        
        await new Promise((resolve) => {
            analyzeProcess.on('close', resolve);
        });
    } catch (error) {
        log.error(`Analysis failed: ${error.message}`);
    }
}

/**
 * Main menu
 */
async function main() {
    console.log(`
${colors.bright}${colors.cyan}════════════════════════════════════════════════════════════════
           PATH ALIAS IMPORT ERROR SOLUTION TOOL
════════════════════════════════════════════════════════════════${colors.reset}

This tool will help you resolve ~100+ path alias import errors in 
your JavaScript/TypeScript project.

${colors.yellow}Select a strategy:${colors.reset}

1. ${colors.green}Convert to Relative Imports${colors.reset} (Recommended)
   - Converts all @/ and ~/ imports to relative paths
   - No build tool configuration needed
   - Works with all JavaScript environments

2. ${colors.blue}Configure Build Tools${colors.reset}
   - Sets up webpack and TypeScript for path aliases
   - Keeps your @ and ~ imports
   - Requires build tool support

3. ${colors.cyan}Browser Import Maps${colors.reset}
   - Modern solution for ES modules in browsers
   - No build step required
   - Requires modern browser support

4. ${colors.yellow}Analyze Only${colors.reset}
   - Show current import issues without fixing

5. ${colors.red}Exit${colors.reset}
`);

    const readline = require('readline');
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    const answer = await new Promise(resolve => {
        rl.question('Enter your choice (1-5): ', resolve);
    });
    rl.close();

    switch (answer.trim()) {
        case '1':
            await analyzeCurrentState();
            await strategyRelativeOnly();
            log.info('\nRun this tool again and choose option 4 to verify all issues are resolved.');
            break;
            
        case '2':
            await strategyConfigureAliases();
            log.info('\nYou may need to update your build scripts to use the new configuration.');
            break;
            
        case '3':
            await strategyCreateImportMap();
            break;
            
        case '4':
            await analyzeCurrentState();
            break;
            
        case '5':
            log.info('Exiting...');
            process.exit(0);
            break;
            
        default:
            log.error('Invalid choice. Please run the script again.');
            process.exit(1);
    }
    
    // Ask if user wants to run another strategy
    console.log('\n');
    const rl2 = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });
    
    const again = await new Promise(resolve => {
        rl2.question('Would you like to try another strategy? (y/n): ', resolve);
    });
    rl2.close();
    
    if (again.toLowerCase() === 'y') {
        await main();
    }
}

// Run the tool
if (require.main === module) {
    main().catch(error => {
        log.error(`Fatal error: ${error.message}`);
        process.exit(1);
    });
}
