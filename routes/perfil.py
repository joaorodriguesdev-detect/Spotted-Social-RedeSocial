from flask import Blueprint, request, redirect, url_for, flash, session, render_template

# Defer imports from `app` into handlers to avoid circular import at module import time.

perfil_bp = Blueprint('perfil', __name__)

@perfil_bp.route('/perfil/<username>')
def perfil(username):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import User, Post, Event, Message, Notification

    user = User.query.filter_by(username=username).first_or_404()
    # Permitir que todos vejam o perfil do admin, incluindo não-admins
    if user.is_admin and not session.get('is_admin'):
        # Não bloquear acesso, apenas mostrar versão pública
        pass
    if user.is_admin:
        posts = Post.query.filter(
            Post.user_id == user.id,
            Post.is_anonymous.is_(False),
            ~Post.content.contains('📢 NOVO EVENTO:')
        ).order_by(Post.timestamp.desc()).limit(10).all()
    else:
        posts = Post.query.filter(
            Post.user_id == user.id,
            Post.is_anonymous.is_(False),
            ~Post.content.contains('📢 NOVO EVENTO:')
        ).order_by(Post.timestamp.desc()).all()
    user_events = Event.query.filter_by(user_id=user.id).order_by(Event.created_at.desc()).all()
    messages = Message.query.filter_by(receiver_id=user.id).order_by(Message.timestamp.desc()).all()
    me = User.query.get(session['user_id'])
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'profile.html',
        user=user,
        posts=posts,
        user_events=user_events,
        messages=messages,
        me=me,
        unread_count=unread
    )


@perfil_bp.route('/perfil_por_remetente')
def perfil_por_remetente():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    sender_name = request.args.get('sender_name', '')
    from app import resolve_user_by_sender_name, User

    user = resolve_user_by_sender_name(sender_name)
    if not user:
        flash('Perfil do remetente nao encontrado.')
        return redirect(request.referrer or url_for('feed.feed'))

    # Permitir que todos vejam o perfil de qualquer usuário
    return redirect(url_for('perfil.perfil', username=user.username))

@perfil_bp.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import User, db, uuid, os, app

    user = User.query.get(session['user_id'])
    name_post = request.form.get('name')
    university_post = request.form.get('university')
    bio_post = request.form.get('bio')
    if name_post:
        user.name = name_post[:80]
        session['name'] = user.name
    if university_post: user.university = university_post[:50]
    if bio_post is not None: user.bio = bio_post[:150]
    file = request.files.get('profile_pic')
    if file and file.filename != '':
        filename_base = f"pfp_{user.id}_{str(uuid.uuid4())[:8]}"
        from app import save_and_optimize_image
        filename = save_and_optimize_image(file, filename_base)
        user.profile_pic = filename
        session['profile_pic'] = filename
    db.session.commit()
    return redirect(url_for('perfil.perfil', username=user.username))

@perfil_bp.route('/seguir/<username>')
def seguir(username):
    from app import User, Notification, db

    if 'user_id' not in session: return redirect(url_for('perfil.perfil', username=username))
    user_to_follow = User.query.filter_by(username=username).first_or_404()
    me = User.query.get(session['user_id'])
    if user_to_follow.id != me.id:
        if not me.is_following(user_to_follow):
            me.followed.append(user_to_follow)
            db.session.add(Notification(user_id=user_to_follow.id, sender_name=me.username, action_type="começou a te seguir"))
        else:
            me.followed.remove(user_to_follow)
        db.session.commit()
    return redirect(url_for('perfil.perfil', username=username))

@perfil_bp.route('/enviar_recado/<int:user_id>', methods=['POST'])
def enviar_recado(user_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    if content:
        from app import Message, Notification, db, User

        sender = session.get('username')
        db.session.add(Message(receiver_id=user_id, sender_name=sender, content=content))
        db.session.add(Notification(user_id=user_id, sender_name=sender, action_type="deixou um recado no mural"))
        db.session.commit()
    return redirect(url_for('perfil.perfil', username=User.query.get(user_id).username))


@perfil_bp.route('/toggle_verificacao/<username>', methods=['POST'])
def toggle_verificacao(username):
    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    from app import User, db

    # Verificar se o usuário atual é administrador
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        flash('Acesso negado. Apenas administradores podem fazer isso.')
        return redirect(url_for('perfil.perfil', username=username))

    # Encontrar o usuário a ser verificado
    user_to_verify = User.query.filter_by(username=username).first_or_404()

    # Não permitir que o admin se desverifique
    if user_to_verify.is_admin:
        flash('Não é possível remover a verificação do admin.')
        return redirect(url_for('perfil.perfil', username=username))

    # Toggle da verificação
    user_to_verify.is_verified = not user_to_verify.is_verified
    db.session.commit()

    status = "verificado" if user_to_verify.is_verified else "desverificado"
    flash(f'Usuário @{username} foi {status} com sucesso.')
    return redirect(url_for('perfil.perfil', username=username))


