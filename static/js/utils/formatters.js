// Formatting utilities
import { escapeHtml } from './dom-helpers.js';

export function formatAgentResponse(text) {
    // First escape HTML
    let formatted = escapeHtml(text);
    
    // Convert headers - reduced spacing
    formatted = formatted.replace(/^###\s+(.+)$/gm, '<h3 class="font-bold text-base text-gray-900 mt-3 mb-2 border-b border-blue-200 pb-1">$1</h3>');
    formatted = formatted.replace(/^##\s+(.+)$/gm, '<h4 class="font-semibold text-sm text-gray-800 mt-2 mb-1">$1</h4>');
    formatted = formatted.replace(/^#\s+(.+)$/gm, '<h3 class="font-bold text-lg text-gray-900 mt-3 mb-2">$1</h3>');
    
    // Convert numbered lists with tighter spacing
    formatted = formatted.replace(/^(\d+)\.\s+(.+)$/gm, '<li class="ml-4 mb-1"><span class="font-semibold text-blue-600">$1.</span> $2</li>');
    
    // Convert bullet points with tighter spacing
    formatted = formatted.replace(/^[-*•]\s+(.+)$/gm, '<li class="ml-4 mb-0.5">• $1</li>');
    
    // Wrap consecutive list items in <ul> tags with reduced padding
    formatted = formatted.replace(/(<li class="ml-4[^"]*">.+<\/li>\n?)+/g, function(match) {
        return '<ul class="list-none space-y-0.5 my-2 pl-2">' + match + '</ul>';
    });
    
    // Convert headers with tighter spacing
    formatted = formatted.replace(/^([A-Za-z0-9\s]+):\s*$/gm, '<h4 class="font-bold text-gray-900 mt-2 mb-1 text-sm">$1:</h4>');
    
    // Convert inline headers with reduced margin
    formatted = formatted.replace(/^([A-Za-z0-9\s]+):\s+(.+)$/gm, '<div class="mb-1 pl-2 border-l-2 border-gray-300"><span class="font-semibold text-gray-800 text-sm">$1:</span> <span class="text-gray-700 text-sm">$2</span></div>');
    
    // Convert code blocks with reduced padding
    formatted = formatted.replace(/```(\w+)?\n?([^`]+)```/g, function(match, lang, code) {
        const language = lang || 'plaintext';
        return `<div class="my-2">
            <div class="bg-gray-700 text-gray-300 px-2 py-0.5 text-xs rounded-t">${language}</div>
            <pre class="bg-gray-800 text-gray-100 p-2 rounded-b text-xs overflow-x-auto"><code>${code.trim()}</code></pre>
        </div>`;
    });
    
    // Convert inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code class="bg-gray-200 px-1 py-0.5 rounded text-xs font-mono text-gray-800">$1</code>');
    
    // Convert bold text
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-gray-900">$1</strong>');
    
    // Convert italic text
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em class="italic text-gray-700">$1</em>');
    
    // Convert line breaks to paragraphs with reduced spacing
    const paragraphs = formatted.split('\n\n');
    formatted = paragraphs
        .filter(p => p.trim())
        .map(p => {
            // Don't wrap if it's already wrapped in a tag
            if (p.trim().startsWith('<')) return p;
            return `<p class="mb-2 text-sm text-gray-700 leading-normal">${p}</p>`;
        })
        .join('\n');
    
    // Convert remaining single line breaks to <br> within paragraphs
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}