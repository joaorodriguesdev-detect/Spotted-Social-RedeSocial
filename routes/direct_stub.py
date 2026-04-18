from flask import Blueprint, request, redirect, url_for, jsonify

# Minimal Direct blueprint stub for local debugging.
# This keeps the server startup fast and avoids circular import issues
# while you iterate on the full Direct implementation.

direct_bp = Blueprint('direct', __name__)


@direct_bp.route('/api/users')
def api_users():
    q = request.args.get('q', '').lower()
    if not q:
        return jsonify([])
    try:
        from app import User
        users = User.query.filter(User.username.like(f'{q}%'), User.is_admin == False).limit(5).all()
        return jsonify([{'username': u.username, 'name': u.name} for u in users])
    except Exception:
        return jsonify([])


@direct_bp.route('/direct')
def direct():
    # Simple redirect to feed while the full Direct blueprint is under repair.
    return redirect(url_for('feed.feed'))

