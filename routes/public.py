import os

from flask import Blueprint, current_app, jsonify, redirect, send_from_directory


public_bp = Blueprint('public', __name__)


@public_bp.route('/public/')
def public_index():
    files = []
    base = current_app.config.get('PUBLIC_FOLDER', os.path.join(current_app.root_path, 'static', 'public'))
    for root, _, filenames in os.walk(base):
        rel_root = os.path.relpath(root, base)
        for name in filenames:
            rel_path = os.path.join(rel_root, name) if rel_root != '.' else name
            files.append(rel_path.replace('\\', '/'))
    return jsonify(sorted(files))


@public_bp.route('/public/<path:filename>')
def public_files(filename):
    return send_from_directory(current_app.config['PUBLIC_FOLDER'], filename)


@public_bp.route('/socket.io/socket.io.js')
def socketio_client_js():
    return redirect('https://cdn.socket.io/4.6.1/socket.io.min.js')

