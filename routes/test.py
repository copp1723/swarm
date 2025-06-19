
from flask import Blueprint, jsonify

test_bp = Blueprint('test', __name__, url_prefix='/api/test')

@test_bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({"success": True, "message": "pong"})

@test_bp.route('/echo', methods=['POST'])
def echo():
    from flask import request
    data = request.get_json()
    return jsonify({"success": True, "echo": data})
