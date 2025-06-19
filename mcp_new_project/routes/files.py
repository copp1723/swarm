from flask import Blueprint, jsonify, request, send_from_directory
import os
import logging
from werkzeug.utils import secure_filename
from services.repository_service import RepositoryService
from config.constants import ALLOWED_EXTENSIONS
from utils.security import validate_file_path, secure_filename_check
from utils.validation import validate_request_data
from utils.response_handler import response_handler, ErrorCategory

files_bp = Blueprint('files', __name__, url_prefix='/api/files')
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

repo_service = RepositoryService()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@files_bp.route('/browse', methods=['GET'])
@response_handler.handle_route_errors(ErrorCategory.UNKNOWN_ERROR)
def browse_directory():
    """Browse directory contents"""
    path = request.args.get('path', '.')
    show_hidden = request.args.get('show_hidden', 'false').lower() == 'true'
    
    # Use new security validation - allow browsing from Desktop
    result = validate_file_path(path, base_directory='/Users/copp1723/Desktop', must_exist=True, must_be_file=False)
    if len(result) == 4:  # Error case returns 4 values
        is_valid, abs_path, error_response, status_code = result
        if not is_valid:
            return error_response, status_code
    else:  # Success case returns 3 values
        is_valid, abs_path, error_response = result
        if not is_valid:
            return error_response
        
    items = []
    if os.path.isdir(abs_path):
        for item in sorted(os.listdir(abs_path)):
            if not show_hidden and item.startswith('.'):
                continue
                
            item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(item_path)
            
            items.append({
                'name': item,
                'path': item_path,  # Use absolute path
                'is_directory': is_dir,
                'size': os.path.getsize(item_path) if not is_dir else None
            })
            
    return {
        'path': path,
        'items': items,
        'total': len(items)
    }

@files_bp.route('/read', methods=['GET'])
@response_handler.handle_route_errors(ErrorCategory.UNKNOWN_ERROR)
def read_file():
    """Read file contents"""
    file_path = request.args.get('path')
    if not file_path:
        return response_handler.error('Path is required', 400)
        
    # Use new security validation
    result = validate_file_path(file_path, must_exist=True, must_be_file=True)
    if len(result) == 4:  # Error case returns 4 values
        is_valid, abs_path, error_response, status_code = result
        if not is_valid:
            return error_response, status_code
    else:  # Success case returns 3 values
        is_valid, abs_path, error_response = result
        if not is_valid:
            return error_response
        
    with open(abs_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    return {
        'path': file_path,
        'content': content,
        'size': len(content),
        'lines': content.count('\n') + 1
    }

@files_bp.route('/analyze', methods=['POST'])
def analyze_repository():
    """Analyze repository structure"""
    try:
        data = request.get_json()
        path = data.get('path', '.')
        include_content = data.get('include_content', False)
        
        analysis = repo_service.analyze_repository(path, include_content)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Error analyzing repository: {e}")
        return jsonify({'error': str(e)}), 500

@files_bp.route('/upload', methods=['POST'])
@response_handler.handle_route_errors(ErrorCategory.UNKNOWN_ERROR)
def upload_file():
    """Upload a file"""
    if 'file' not in request.files:
        return response_handler.error('No file provided', 400)
        
    file = request.files['file']
    if file.filename == '':
        return response_handler.error('No file selected', 400)
        
    # Use new security validation
    is_valid_filename, filename_error = secure_filename_check(file.filename, ALLOWED_EXTENSIONS)
    if not is_valid_filename:
        return response_handler.error(filename_error, 400)
        
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)
    
    return {
        'filename': filename,
        'path': file_path,
        'size': os.path.getsize(file_path)
    }

@files_bp.route('/download/<path:file_path>')
def download_file(file_path):
    """Download a file"""
    try:
        # Security check
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(os.path.abspath('.')):
            return jsonify({'error': 'Invalid path'}), 403
            
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)
        
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return jsonify({'error': str(e)}), 500