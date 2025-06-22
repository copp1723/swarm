#!/usr/bin/env node

/**
 * Script to analyze all import statements in JavaScript/TypeScript files
 * and identify potential path alias issues
 */

const fs = require('fs').promises;
const path = require('path');

// Configuration
const PROJECT_ROOT = path.join(__dirname, '../../');
const STATIC_JS_DIR = path.join(PROJECT_ROOT, 'static/js');
const IGNORE_DIRS = ['node_modules', '.git', 'dist', 'build', 'coverage', 'venv', '__pycache__'];
const FILE_EXTENSIONS = ['.js', '.jsx', '.ts', '.tsx', '.mjs'];

// Regular expressions for different import patterns
const IMPORT_REGEX = /(?:import|export)\s+(?:(?:\{[^}]*\}|[\w,\s*]+)\s+from\s+)?['"]([^'"]+)['"]/g;
const REQUIRE_REGEX = /require\(['"]([^'"]+)['"]\)/g;
const DYNAMIC_IMPORT_REGEX = /import\(['"]([^'"]+)['"]\)/g;

// Statistics
const stats = {
    totalFiles: 0,
    filesWithImports: 0,
    totalImports: 0,
    relativeImports: 0,
    aliasImports: 0,
    nodeModuleImports: 0,
    problematicImports: [],
    importPatterns: new Map(),
    fileErrors: []
};

/**
 * Check if a path should be ignored
 */
function shouldIgnore(filePath) {
    return IGNORE_DIRS.some(dir => filePath.includes(`/${dir}/`) || filePath.includes(`\\${dir}\\`));
}

/**
 * Get all JavaScript/TypeScript files recursively
 */
async function getJavaScriptFiles(dir, fileList = []) {
    try {
        const files = await fs.readdir(dir);
        
        for (const file of files) {
            const filePath = path.join(dir, file);
            
            if (shouldIgnore(filePath)) continue;
            
            const stat = await fs.stat(filePath);
            
            if (stat.isDirectory()) {
                await getJavaScriptFiles(filePath, fileList);
            } else if (FILE_EXTENSIONS.includes(path.extname(file))) {
                fileList.push(filePath);
            }
        }
    } catch (error) {
        console.error(`Error reading directory ${dir}:`, error.message);
    }
    
    return fileList;
}

/**
 * Analyze imports in a file
 */
async function analyzeFile(filePath) {
    try {
        const content = await fs.readFile(filePath, 'utf8');
        const relativePath = path.relative(PROJECT_ROOT, filePath);
        
        const imports = [];
        
        // Find all import statements
        let match;
        
        // ES6 imports/exports
        const importRegex = new RegExp(IMPORT_REGEX);
        while ((match = importRegex.exec(content)) !== null) {
            imports.push({
                type: 'import',
                path: match[1],
                line: content.substring(0, match.index).split('\n').length
            });
        }
        
        // CommonJS requires
        const requireRegex = new RegExp(REQUIRE_REGEX);
        while ((match = requireRegex.exec(content)) !== null) {
            imports.push({
                type: 'require',
                path: match[1],
                line: content.substring(0, match.index).split('\n').length
            });
        }
        
        // Dynamic imports
        const dynamicRegex = new RegExp(DYNAMIC_IMPORT_REGEX);
        while ((match = dynamicRegex.exec(content)) !== null) {
            imports.push({
                type: 'dynamic',
                path: match[1],
                line: content.substring(0, match.index).split('\n').length
            });
        }
        
        if (imports.length > 0) {
            stats.filesWithImports++;
            
            for (const imp of imports) {
                stats.totalImports++;
                
                // Categorize the import
                if (imp.path.startsWith('./') || imp.path.startsWith('../')) {
                    stats.relativeImports++;
                    
                    // Check if relative import exists
                    const resolvedPath = await resolveImportPath(filePath, imp.path);
                    if (!resolvedPath) {
                        stats.problematicImports.push({
                            file: relativePath,
                            import: imp.path,
                            line: imp.line,
                            type: 'missing-file',
                            message: 'Imported file not found'
                        });
                    }
                } else if (imp.path.startsWith('@') || imp.path.startsWith('~')) {
                    stats.aliasImports++;
                    stats.problematicImports.push({
                        file: relativePath,
                        import: imp.path,
                        line: imp.line,
                        type: 'path-alias',
                        message: 'Path alias not configured'
                    });
                } else if (!imp.path.includes('/') || isNodeBuiltin(imp.path)) {
                    stats.nodeModuleImports++;
                } else {
                    // Check for other problematic patterns
                    if (!imp.path.startsWith('/') && imp.path.includes('/')) {
                        stats.problematicImports.push({
                            file: relativePath,
                            import: imp.path,
                            line: imp.line,
                            type: 'ambiguous',
                            message: 'Ambiguous import path - might need alias or relative path'
                        });
                    }
                }
                
                // Track import patterns
                const pattern = getImportPattern(imp.path);
                stats.importPatterns.set(pattern, (stats.importPatterns.get(pattern) || 0) + 1);
            }
        }
        
    } catch (error) {
        stats.fileErrors.push({
            file: path.relative(PROJECT_ROOT, filePath),
            error: error.message
        });
    }
}

/**
 * Resolve import path to check if file exists
 */
async function resolveImportPath(fromFile, importPath) {
    const dir = path.dirname(fromFile);
    const resolvedPath = path.resolve(dir, importPath);
    
    // Try with different extensions
    const extensions = ['', '.js', '.jsx', '.ts', '.tsx', '.json', '/index.js', '/index.ts'];
    
    for (const ext of extensions) {
        try {
            const fullPath = resolvedPath + ext;
            await fs.access(fullPath);
            return fullPath;
        } catch (error) {
            // File doesn't exist with this extension
        }
    }
    
    return null;
}

/**
 * Check if import is a Node.js built-in module
 */
function isNodeBuiltin(moduleName) {
    const builtins = [
        'fs', 'path', 'http', 'https', 'crypto', 'os', 'util', 'stream',
        'buffer', 'child_process', 'cluster', 'events', 'querystring', 'url'
    ];
    return builtins.includes(moduleName.split('/')[0]);
}

/**
 * Get import pattern for categorization
 */
function getImportPattern(importPath) {
    if (importPath.startsWith('@')) return '@-alias';
    if (importPath.startsWith('~')) return '~-alias';
    if (importPath.startsWith('./')) return 'relative-current';
    if (importPath.startsWith('../')) return 'relative-parent';
    if (importPath.startsWith('/')) return 'absolute';
    if (!importPath.includes('/')) return 'module';
    return 'other';
}

/**
 * Generate report
 */
function generateReport() {
    console.log('\n═══════════════════════════════════════════════════════════════');
    console.log('                    IMPORT ANALYSIS REPORT                      ');
    console.log('═══════════════════════════════════════════════════════════════\n');
    
    console.log('📊 SUMMARY:');
    console.log(`   Total files scanned: ${stats.totalFiles}`);
    console.log(`   Files with imports: ${stats.filesWithImports}`);
    console.log(`   Total import statements: ${stats.totalImports}`);
    console.log(`   - Relative imports: ${stats.relativeImports}`);
    console.log(`   - Path alias imports: ${stats.aliasImports}`);
    console.log(`   - Node module imports: ${stats.nodeModuleImports}`);
    console.log(`   - Problematic imports: ${stats.problematicImports.length}\n`);
    
    if (stats.problematicImports.length > 0) {
        console.log('🚨 PROBLEMATIC IMPORTS:');
        
        // Group by type
        const byType = {};
        stats.problematicImports.forEach(prob => {
            if (!byType[prob.type]) byType[prob.type] = [];
            byType[prob.type].push(prob);
        });
        
        for (const [type, problems] of Object.entries(byType)) {
            console.log(`\n   ${type.toUpperCase()} (${problems.length} issues):`);
            problems.slice(0, 10).forEach(prob => {
                console.log(`   - ${prob.file}:${prob.line}`);
                console.log(`     Import: "${prob.import}"`);
                console.log(`     Issue: ${prob.message}`);
            });
            if (problems.length > 10) {
                console.log(`   ... and ${problems.length - 10} more`);
            }
        }
    }
    
    console.log('\n📈 IMPORT PATTERNS:');
    const sortedPatterns = Array.from(stats.importPatterns.entries())
        .sort((a, b) => b[1] - a[1]);
    
    sortedPatterns.forEach(([pattern, count]) => {
        console.log(`   ${pattern}: ${count} occurrences`);
    });
    
    if (stats.fileErrors.length > 0) {
        console.log('\n⚠️  FILE ERRORS:');
        stats.fileErrors.slice(0, 5).forEach(err => {
            console.log(`   - ${err.file}: ${err.error}`);
        });
        if (stats.fileErrors.length > 5) {
            console.log(`   ... and ${stats.fileErrors.length - 5} more`);
        }
    }
    
    console.log('\n═══════════════════════════════════════════════════════════════\n');
}

/**
 * Main function
 */
async function main() {
    console.log('🔍 Analyzing imports in the project...\n');
    
    // Get all JavaScript files
    const files = await getJavaScriptFiles(STATIC_JS_DIR);
    stats.totalFiles = files.length;
    
    console.log(`Found ${files.length} JavaScript/TypeScript files to analyze...`);
    
    // Analyze each file
    for (let i = 0; i < files.length; i++) {
        await analyzeFile(files[i]);
        
        // Progress indicator
        if ((i + 1) % 50 === 0) {
            console.log(`   Analyzed ${i + 1}/${files.length} files...`);
        }
    }
    
    // Generate report
    generateReport();
    
    // Save detailed report
    const reportPath = path.join(__dirname, 'import-analysis-report.json');
    await fs.writeFile(reportPath, JSON.stringify({
        summary: {
            totalFiles: stats.totalFiles,
            filesWithImports: stats.filesWithImports,
            totalImports: stats.totalImports,
            relativeImports: stats.relativeImports,
            aliasImports: stats.aliasImports,
            nodeModuleImports: stats.nodeModuleImports
        },
        problematicImports: stats.problematicImports,
        importPatterns: Object.fromEntries(stats.importPatterns),
        fileErrors: stats.fileErrors
    }, null, 2));
    
    console.log(`\n📄 Detailed report saved to: ${reportPath}`);
    
    // Exit with error code if there are problematic imports
    if (stats.problematicImports.length > 0) {
        console.log(`\n❌ Found ${stats.problematicImports.length} import issues that need to be fixed.`);
        process.exit(1);
    } else {
        console.log('\n✅ No import issues found!');
        process.exit(0);
    }
}

// Run the script
if (require.main === module) {
    main().catch(error => {
        console.error('Error running import analysis:', error);
        process.exit(1);
    });
}

module.exports = { analyzeFile, getJavaScriptFiles };
