# Template routes for dynamic template loading
from flask import Blueprint, jsonify, render_template_string
import os

templates_bp = Blueprint('templates', __name__)

@templates_bp.route('/api/templates/<template_name>')
def get_template(template_name):
    """Serve HTML templates dynamically"""
    allowed_templates = [
        'chat-container',
        'agent-sidebar', 
        'collaboration-modal',
        'directory-browser',
        'three-way-chat'
    ]
    
    if template_name not in allowed_templates:
        return jsonify({'error': 'Template not found'}), 404
    
    template_path = f'static/templates/partials/{template_name}.html'
    
    if not os.path.exists(template_path):
        return jsonify({'error': 'Template file not found'}), 404
    
    try:
        with open(template_path, 'r') as f:
            content = f.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@templates_bp.route('/api/templates')
def list_templates():
    """List all available templates"""
    templates_dir = 'static/templates/partials'
    templates = []
    
    if os.path.exists(templates_dir):
        for filename in os.listdir(templates_dir):
            if filename.endswith('.html'):
                template_name = filename[:-5]  # Remove .html extension
                templates.append({
                    'name': template_name,
                    'filename': filename
                })
    
    return jsonify({'success': True, 'templates': templates})