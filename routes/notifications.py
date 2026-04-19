from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from extensions import socketio
from models import Notification, User, db


notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/denunciar', methods=['POST'])
def denunciar():
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado'}), 401

    data = request.get_json(silent=True) or {}
    post_id = data.get('post_id')
    descricao = data.get('descricao')

    if not post_id or not descricao:
        return jsonify({'error': 'Dados inválidos'}), 400

    sender_name = session.get('username')
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        db.session.add(
            Notification(
                user_id=admin.id,
                sender_name=sender_name,
                action_type=f'denunciou uma postagem: {descricao[:50]}',
                post_id=post_id,
                category='report',
            )
        )
    db.session.commit()
    return jsonify({'ok': True})


@notifications_bp.route('/notificacoes')
def notificacoes():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.timestamp.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notifs, unread_count=0)


@notifications_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
def api_mark_notification_read(notif_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401

    user_id = session.get('user_id')
    notif = Notification.query.get(notif_id)
    if not notif or notif.user_id != user_id:
        return jsonify({'error': 'notificacao nao encontrada'}), 404

    if not notif.is_read:
        notif.is_read = True
        db.session.commit()

    try:
        unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        socketio.emit('notification:marked-read', {'unread_count': unread_count}, room=f'user:{user_id}')
    except Exception:
        pass

    return jsonify({'ok': True, 'unread_count': Notification.query.filter_by(user_id=user_id, is_read=False).count()})

