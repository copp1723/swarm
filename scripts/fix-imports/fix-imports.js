#!/usr/bin/env node

/**
 * Script to fix import issues in JavaScript/TypeScript files
 * This will convert path aliases to relative imports and fix missing extensions
 */

const fs = require('fs').promises;
const path = require('path');

// Configuration
const PROJECT_ROOT = path.join(__dirname, '../../');
const STATIC_JS_DIR = path.join(PROJECT_ROOT, 'static/js');

// Path alias mappings (if any were configured)
const PATH_ALIASES = {
    '@': STATIC_JS_DIR,
    '~': STATIC_JS_DIR,
    '@components': path.join(STATIC_JS_DIR, 'components'),
    '@services': path.join(STATIC_JS_DIR, 'services'),
    '@utils': path.join(STATIC_JS_DIR, 'utils'),
    '@agents': path.join(STATIC_JS_DIR, 'agents'),
    '~/components': path.join(STATIC_JS_DIR, 'components'),
    '~/services': path.join(STATIC_JS_DIR, 'services'),
    '~/utils': path.join(STATIC_JS_DIR, 'utils'),
    '~/agents': path.join(STATIC_JS_DIR, 'agents')
};

// Statistics
const fixStats = {
    filesProcessed: 0,
    filesModified: 0,
    importsFixed: 0,
    errors: []
};

/**
 * Convert path alias to relative import
 */
function convertAliasToRelative(fromFile, importPath) {
    // Check each alias
    for (const [alias, absolutePath] of Object.entries(PATH_ALIASES)) {
        if (importPath.startsWith(alias)) {
            // Replace alias with absolute path
            const resolvedPath = importPath.replace(alias, absolutePath);
            
            // Calculate relative path from the importing file
            const fromDir = path.dirname(fromFile);
            let relativePath = path.relative(fromDir, resolvedPath);
            
            // Ensure path starts with ./ or ../
            if (!relativePath.startsWith('.')) {
                relativePath = './' + relativePath;
            }
            
            // Convert backslashes to forward slashes for consistency
            relativePath = relativePath.replace(/\\/g, '/');
            
            return relativePath;
        }
    }
    
    return null;
}

/**
 * Fix imports in a file
 */
async function fixFileImports(filePath) {
    try {
        const content = await fs.readFile(filePath, 'utf8');
        let modifiedContent = content;
        let modified = false;
        
        // Regular expressions for different import types
        const importPatterns = [
            // ES6 imports
            {
                regex: /import\s+(.+?)\s+from\s+['"]([^'"]+)['"]/g,
                replace: (match, imports, importPath) => {
                    const fixed = fixImportPath(filePath, importPath);
                    if (fixed !== importPath) {
                        modified = true;
                        fixStats.importsFixed++;
                        return `import ${imports} from '${fixed}'`;
                    }
                    return match;
                }
            },
            // ES6 exports
            {
                regex: /export\s+(.+?)\s+from\s+['"]([^'"]+)['"]/g,
                replace: (match, exports, importPath) => {
                    const fixed = fixImportPath(filePath, importPath);
                    if (fixed !== importPath) {
                        modified = true;
                        fixStats.importsFixed++;
                        return `export ${exports} from '${fixed}'`;
                    }
                    return match;
                }
            },
            // Dynamic imports
            {
                regex: /import\(['"]([^'"]+)['"]\)/g,
                replace: (match, importPath) => {
                    const fixed = fixImportPath(filePath, importPath);
                    if (fixed !== importPath) {
                        modified = true;
                        fixStats.importsFixed++;
                        return `import('${fixed}')`;
                    }
                    return match;
                }
            },
            // CommonJS requires
            {
                regex: /require\(['"]([^'"]+)['"]\)/g,
                replace: (match, importPath) => {
                    const fixed = fixImportPath(filePath, importPath);
                    if (fixed !== importPath) {
                        modified = true;
                        fixStats.importsFixed++;
                        return `require('${fixed}')`;
                    }
                    return match;
                }
            }
        ];
        
        // Apply fixes
        for (const pattern of importPatterns) {
            modifiedContent = modifiedContent.replace(pattern.regex, pattern.replace);
        }
        
        // Write back if modified
        if (modified) {
            await fs.writeFile(filePath, modifiedContent, 'utf8');
            fixStats.filesModified++;
            console.log(`✅ Fixed imports in: ${path.relative(PROJECT_ROOT, filePath)}`);
        }
        
        fixStats.filesProcessed++;
        
    } catch (error) {
        fixStats.errors.push({
            file: path.relative(PROJECT_ROOT, filePath),
            error: error.message
        });
    }
}

/**
 * Fix an import path
 */
function fixImportPath(fromFile, importPath) {
    // Skip node modules and already relative imports
    if (!importPath.startsWith('@') && !importPath.startsWith('~')) {
        // Check if it needs .js extension (for local files)
        if (importPath.startsWith('./') || importPath.startsWith('../')) {
            if (!importPath.endsWith('.js') && !importPath.endsWith('.json')) {
                // Check if the file exists without extension
                const resolved = path.resolve(path.dirname(fromFile), importPath);
                try {
                    // Try to find the actual file
                    const extensions = ['.js', '.jsx', '.ts', '.tsx'];
                    for (const ext of extensions) {
                        try {
                            require('fs').accessSync(resolved + ext);
                            return importPath + '.js'; // Add .js extension for ES modules
                        } catch (e) {
                            // Try next extension
                        }
                    }
                } catch (e) {
                    // Keep original if can't resolve
                }
            }
        }
        return importPath;
    }
    
    // Convert alias to relative path
    const relative = convertAliasToRelative(fromFile, importPath);
    if (relative) {
        // Add .js extension if needed
        if (!relative.endsWith('.js') && !relative.endsWith('.json')) {
            return relative + '.js';
        }
        return relative;
    }
    
    // Return original if can't convert
    return importPath;
}

/**
 * Get all JavaScript files
 */
async function getJavaScriptFiles(dir, fileList = []) {
    const files = await fs.readdir(dir);
    
    for (const file of files) {
        const filePath = path.join(dir, file);
        const stat = await fs.stat(filePath);
        
        if (stat.isDirectory()) {
            if (!['node_modules', '.git', 'dist', 'build'].includes(file)) {
                await getJavaScriptFiles(filePath, fileList);
            }
        } else if (['.js', '.jsx', '.ts', '.tsx'].includes(path.extname(file))) {
            fileList.push(filePath);
        }
    }
    
    return fileList;
}

/**
 * Main function
 */
async function main() {
    console.log('🔧 Fixing import issues in JavaScript/TypeScript files...\n');
    
    // First, run analysis to find issues
    console.log('📊 Running import analysis...');
    const { analyzeFile, getJavaScriptFiles: getFiles } = require('./analyze-imports');
    
    // Get all files
    const files = await getJavaScriptFiles(STATIC_JS_DIR);
    console.log(`Found ${files.length} files to process...\n`);
    
    // Process each file
    for (let i = 0; i < files.length; i++) {
        await fixFileImports(files[i]);
        
        // Progress indicator
        if ((i + 1) % 50 === 0) {
            console.log(`   Processed ${i + 1}/${files.length} files...`);
        }
    }
    
    // Report results
    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('                    FIX IMPORTS SUMMARY                         ');
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    console.log(`📊 Results:`);
    console.log(`   Files processed: ${fixStats.filesProcessed}`);
    console.log(`   Files modified: ${fixStats.filesModified}`);
    console.log(`   Imports fixed: ${fixStats.importsFixed}`);
    
    if (fixStats.errors.length > 0) {
        console.log(`\n⚠️  Errors (${fixStats.errors.length}):`);
        fixStats.errors.forEach(err => {
            console.log(`   - ${err.file}: ${err.error}`);
        });
    }
    
    console.log('\n═══════════════════════════════════════════════════════════════\n');
    
    if (fixStats.importsFixed > 0) {
        console.log('✅ Import fixes completed successfully!');
        console.log('   Run the analyze-imports.js script again to verify all issues are resolved.');
    } else {
        console.log('ℹ️  No import issues found that needed fixing.');
    }
}

// Run the script
if (require.main === module) {
    main().catch(error => {
        console.error('Error fixing imports:', error);
        process.exit(1);
    });
}
