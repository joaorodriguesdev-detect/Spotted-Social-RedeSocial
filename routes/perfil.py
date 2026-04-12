from flask import Blueprint, request, redirect, url_for, flash, session, render_template

# Defer imports from `app` into handlers to avoid circular import at module import time.

perfil_bp = Blueprint('perfil', __name__)

@perfil_bp.route('/perfil/<username>')
def perfil(username):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import User, Post, Event, Message, Notification

    user = User.query.filter_by(username=username).first_or_404()
    if user.is_admin and not session.get('is_admin'): return redirect(url_for('feed'))
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
        return redirect(request.referrer or url_for('feed'))

    if user.is_admin and not session.get('is_admin'):
        return redirect(url_for('feed'))

    return redirect(url_for('perfil', username=user.username))

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
        ext = os.path.splitext(file.filename)[1]
        filename = f"pfp_{user.id}_{str(uuid.uuid4())[:8]}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user.profile_pic = filename
        session['profile_pic'] = filename
    db.session.commit()
    return redirect(url_for('perfil', username=user.username))

@perfil_bp.route('/seguir/<username>')
def seguir(username):
    from app import User, Notification, db

    if 'user_id' not in session: return redirect(url_for('perfil', username=username))
    user_to_follow = User.query.filter_by(username=username).first_or_404()
    me = User.query.get(session['user_id'])
    if user_to_follow.id != me.id:
        if not me.is_following(user_to_follow):
            me.followed.append(user_to_follow)
            db.session.add(Notification(user_id=user_to_follow.id, sender_name=me.username, action_type="começou a te seguir"))
        else:
            me.followed.remove(user_to_follow)
        db.session.commit()
    return redirect(url_for('perfil', username=username))

@perfil_bp.route('/enviar_recado/<int:user_id>', methods=['POST'])
def enviar_recado(user_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('content')
    if content:
        from app import Message, Notification, db

        sender = session.get('username')
        db.session.add(Message(receiver_id=user_id, sender_name=sender, content=content))
        db.session.add(Notification(user_id=user_id, sender_name=sender, action_type="deixou um recado no mural"))
        db.session.commit()
    return redirect(url_for('perfil', username=User.query.get(user_id).username))
