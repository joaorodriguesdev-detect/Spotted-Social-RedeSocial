import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def welcome():
    if 'user_id' in session:
        return redirect(url_for('feed.feed'))
    return render_template('welcome.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    username = (request.form.get('username') or '').lower().strip()
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        session.clear()
        session['user_id'] = user.id
        session['username'] = user.username
        session['name'] = user.name
        session['is_admin'] = user.is_admin
        session['profile_pic'] = user.profile_pic
        session.permanent = True
        return redirect(url_for('feed.feed'))
    flash('Usuário ou senha incorretos.')
    return redirect(url_for('welcome'))


@auth_bp.route('/registro', methods=['POST'])
def registro():
    name = (request.form.get('name') or '').strip()
    username = (request.form.get('username') or '').lower().strip()
    password = request.form.get('password') or ''
    confirm_password = request.form.get('confirm_password') or ''
    university = request.form.get('university')

    if ' ' in username:
        flash('O usuário não pode conter espaços.')
        return redirect(url_for('welcome'))

    if password != confirm_password:
        flash('As senhas não coincidem.')
        return redirect(url_for('welcome'))

    # Require at least 8 chars and one special char from the allowed hint set.
    if len(password) < 8 or not re.search(r'[#@$%*]', password):
        flash('Senha inválida. Use 8+ caracteres e inclua ao menos um de: # @ $ % *')
        return redirect(url_for('welcome'))

    if User.query.filter_by(username=username).first():
        flash('Login já existe.')
        return redirect(url_for('welcome'))

    user = User(name=name, username=username, password=generate_password_hash(password), university=university)
    db.session.add(user)
    db.session.commit()

    session.clear()
    session['user_id'] = user.id
    session['username'] = user.username
    session['name'] = user.name
    session['is_admin'] = False
    session['profile_pic'] = user.profile_pic
    session.permanent = True
    return redirect(url_for('feed.feed'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você foi desconectado com sucesso.')
    return redirect(url_for('welcome'))
