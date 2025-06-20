// Directory Browser Component
import { FileAPI } from '../services/api.js';
import { createElement, escapeHtml, updateIcons } from '../utils/dom-helpers.js';

export class DirectoryBrowser {
    constructor() {
        this.fileAPI = new FileAPI();
        this.currentPath = '/Users/copp1723/Desktop';
        this.onSelect = null;
        this.modal = null;
    }

    async open(initialPath = null) {
        this.currentPath = initialPath || this.currentPath;
        
        // Create modal
        this.modal = createElement('div', 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50');
        this.modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden">
                <h3 class="text-lg font-semibold mb-4">Select Directory</h3>
                <div class="mb-4">
                    <div class="flex items-center space-x-2 mb-2">
                        <span class="text-sm text-gray-600">Current Path:</span>
                        <span id="browser-current-path" class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">${escapeHtml(this.currentPath)}</span>
                    </div>
                    <button id="browser-navigate-up" class="text-sm text-blue-600 hover:underline">Go up ↑</button>
                </div>
                <div id="browser-directory-list" class="border rounded-lg p-4 h-96 overflow-y-auto bg-gray-50">
                    <div class="text-center text-gray-500">Loading...</div>
                </div>
                <div class="mt-4 flex justify-end space-x-2">
                    <button id="browser-cancel" class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                    <button id="browser-select" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Select This Directory</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.modal);
        
        // Attach event listeners
        document.getElementById('browser-navigate-up').addEventListener('click', () => this.navigateUp());
        document.getElementById('browser-cancel').addEventListener('click', () => this.close());
        document.getElementById('browser-select').addEventListener('click', () => this.selectCurrent());
        
        // Load initial directory
        await this.loadDirectory(this.currentPath);
        
        return new Promise((resolve) => {
            this.onSelect = resolve;
        });
    }

    async loadDirectory(path) {
        try {
            const response = await this.fileAPI.browseDirectory(path);
            
            if (!response.data) {
                throw new Error(response.error || 'Failed to load directory');
            }
            
            const dirList = document.getElementById('browser-directory-list');
            dirList.innerHTML = '';
            
            // Update current path display
            this.currentPath = path;
            document.getElementById('browser-current-path').textContent = path;
            
            const items = response.data.items || [];
            
            // Sort directories first, then files
            const directories = items.filter(item => item.is_directory).sort((a, b) => a.name.localeCompare(b.name));
            const files = items.filter(item => !item.is_directory).sort((a, b) => a.name.localeCompare(b.name));
            
            // Add directories
            directories.forEach(dir => {
                const dirDiv = createElement('div', 'flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer');
                dirDiv.innerHTML = `
                    <i data-lucide="folder" class="w-4 h-4 text-yellow-600"></i>
                    <span class="text-sm">${escapeHtml(dir.name)}</span>
                `;
                dirDiv.addEventListener('click', () => this.loadDirectory(dir.path));
                dirList.appendChild(dirDiv);
            });
            
            // Add files (display only)
            files.forEach(file => {
                const fileDiv = createElement('div', 'flex items-center space-x-2 p-2 text-gray-500');
                fileDiv.innerHTML = `
                    <i data-lucide="file" class="w-4 h-4"></i>
                    <span class="text-sm">${escapeHtml(file.name)}</span>
                `;
                dirList.appendChild(fileDiv);
            });
            
            updateIcons();
            
            if (directories.length === 0 && files.length === 0) {
                dirList.innerHTML = '<div class="text-center text-gray-500 text-sm">Empty directory</div>';
            }
            
        } catch (error) {
            console.error('Error loading directory:', error);
            const dirList = document.getElementById('browser-directory-list');
            dirList.innerHTML = `<div class="text-center text-red-500 text-sm">Error: ${escapeHtml(error.message)}</div>`;
        }
    }

    navigateUp() {
        const parentPath = this.currentPath.substring(0, this.currentPath.lastIndexOf('/')) || '/';
        this.loadDirectory(parentPath);
    }

    selectCurrent() {
        if (this.onSelect) {
            this.onSelect(this.currentPath);
        }
        this.close();
    }

    close() {
        if (this.modal) {
            this.modal.remove();
            this.modal = null;
        }
        if (this.onSelect) {
            this.onSelect(null);
        }
    }
}
//# sourceMappingURL=directory-browser.js.map
