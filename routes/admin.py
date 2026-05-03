from flask import Blueprint, flash, redirect, session, url_for

from models import User, db


admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/toggle_verificacao/<username>', methods=['POST'])
def toggle_verificacao(username):
    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        flash('Acesso negado. Apenas administradores podem fazer isso.')
        return redirect(url_for('perfil.perfil', username=username))

    user_to_verify = User.query.filter_by(username=username).first_or_404()

    if user_to_verify.is_admin:
        flash('Não é possível remover a verificação do admin.')
        return redirect(url_for('perfil.perfil', username=username))

    user_to_verify.is_verified = not user_to_verify.is_verified
    db.session.commit()

    status = 'verificado' if user_to_verify.is_verified else 'desverificado'
    flash(f'Usuário @{username} foi {status} com sucesso.')
    return redirect(url_for('perfil.perfil', username=username))

