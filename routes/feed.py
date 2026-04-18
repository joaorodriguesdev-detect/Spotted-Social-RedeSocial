from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template, session
from sqlalchemy import or_

# Avoid importing `app` at module import time to prevent circular imports.
# Import necessary symbols from `app` inside route handlers where needed.

feed_bp = Blueprint('feed', __name__)

@feed_bp.route('/feed')
def feed():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import get_feed_chunk, annotate_posts_with_like_info, Notification

    posts, has_more, next_cursor_ts, next_cursor_id = get_feed_chunk()
    annotate_posts_with_like_info(posts, session.get('user_id'))
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'index.html',
        posts=posts,
        unread_count=unread,
        has_more=has_more,
        next_cursor_ts=next_cursor_ts,
        next_cursor_id=next_cursor_id
    )


@feed_bp.route('/feed/more')
def feed_more():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401

    cursor_ts_raw = request.args.get('cursor_ts')
    cursor_id_raw = request.args.get('cursor_id')

    cursor_ts = None
    cursor_id = None
    if cursor_ts_raw and cursor_id_raw:
        try:
            from app import datetime
            cursor_ts = datetime.fromisoformat(cursor_ts_raw)
            cursor_id = int(cursor_id_raw)
        except (TypeError, ValueError):
            return jsonify({'error': 'cursor invalido'}), 400

    from app import get_feed_chunk, annotate_posts_with_like_info

    posts, has_more, next_cursor_ts, next_cursor_id = get_feed_chunk(
        cursor_ts=cursor_ts,
        cursor_id=cursor_id
    )
    # Annotate posts with liked_by_me to allow client-side partial to render like state without per-post queries
    annotate_posts_with_like_info(posts, session.get('user_id'))
    html = render_template('_feed_posts.html', posts=posts)
    return jsonify({
        'html': html,
        'has_more': has_more,
        'next_cursor_ts': next_cursor_ts,
        'next_cursor_id': next_cursor_id
    })

@feed_bp.route('/search')
def search():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import normalize_search_category, Notification, Post, Event, User

    query = request.args.get('query', '').lower().strip().replace('@', '')
    category = normalize_search_category(request.args.get('category'))
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    if not query:
        posts = Post.query.order_by(Post.timestamp.desc()).all()
        return render_template(
            'index.html',
            searching=True,
            query='',
            posts=posts,
            unread_count=unread,
            search_category=category,
            search_results=[],
            event_results=[]
        )

    if category == 'eventos':
        event_results = Event.query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%')
            )
        ).order_by(Event.created_at.desc()).all()
        return render_template(
            'index.html',
            event_results=event_results,
            search_results=[],
            query=query,
            searching=True,
            unread_count=unread,
            search_category=category
        )

    results = User.query.filter(User.username.contains(query), User.is_admin == False).all()
    return render_template(
        'index.html',
        search_results=results,
        event_results=[],
        query=query,
        searching=True,
        unread_count=unread,
        search_category=category
    )


@feed_bp.route('/api/search')
def api_search():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    from app import normalize_search_category, Event, User

    query = (request.args.get('query') or '').lower().strip().replace('@', '')
    category = normalize_search_category(request.args.get('category'))

    if not query:
        return jsonify({'category': category, 'query': query, 'users': [], 'events': []})

    if category == 'eventos':
        events = Event.query.filter(
            or_(
                Event.title.ilike(f'%{query}%'),
                Event.location.ilike(f'%{query}%'),
                Event.description.ilike(f'%{query}%')
            )
        ).order_by(Event.created_at.desc()).limit(20).all()

        payload = []
        for event in events:
            event_date_parts = (event.event_date or '').split(' às ')
            raw_event_date = event_date_parts[0] if event_date_parts and event_date_parts[0] else (event.event_date or '')
            parsed = raw_event_date.split('-')
            event_date_label = raw_event_date
            if len(parsed) == 3:
                event_date_label = f"{parsed[2]}/{parsed[1]}/{parsed[0]}"
            payload.append({
                'id': event.id,
                'title': event.title,
                'description': event.description,
                'location': event.location,
                'media_url': event.media_url,
                'event_date_label': event_date_label,
                'creator_username': event.creator.username if event.creator else ''
            })

        return jsonify({'category': category, 'query': query, 'users': [], 'events': payload})

    users = User.query.filter(User.username.contains(query), User.is_admin == False).limit(20).all()
    return jsonify({
        'category': category,
        'query': query,
        'users': [{'username': u.username, 'name': u.name} for u in users],
        'events': []
    })

@feed_bp.route('/postar', methods=['POST'])
def postar():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import Post, db, uuid, os, notify_mentions

    content = request.form.get('content')
    anon_mode = request.form.get('anon_mode') == 'true'
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        # Convert uploaded image to webp and use returned filename
        filename_base = str(uuid.uuid4())
        from app import save_and_optimize_image
        filename = save_and_optimize_image(file, filename_base)
    new_post = Post(content=content, media_url=filename, user_id=session.get('user_id'), is_anonymous=anon_mode)
    db.session.add(new_post)
    db.session.flush() 
    if not anon_mode:
        notify_mentions(content, session.get('name'), new_post.id)
    db.session.commit()
    return redirect(url_for('feed.feed'))

@feed_bp.route('/excluir_post/<int:post_id>')
def excluir_post(post_id):
    from app import Post, db
    post = Post.query.get_or_404(post_id)
    if (post.user_id == session.get('user_id') and post.user_id is not None) or session.get('is_admin'):
        db.session.delete(post)
        db.session.commit()
    return redirect(request.referrer or url_for('feed.feed'))

@feed_bp.route('/like/<int:post_id>')
def like(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import Post, User, db, Notification
    post = Post.query.get_or_404(post_id)
    user = User.query.get(session['user_id'])
    if post not in user.liked_posts:
        user.liked_posts.append(post)
        post.likes += 1
        if post.user_id and post.user_id != user.id:
            db.session.add(Notification(user_id=post.user_id, sender_name=user.name, action_type="curtiu sua publicação", post_id=post.id))
    else:
        user.liked_posts.remove(post)
        post.likes -= 1
    db.session.commit()
    # If the request is AJAX, return JSON so the client can update UI without full redirect.
    try:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json
    except Exception:
        is_ajax = False

    liked = post.liked_by.filter_by(id=user.id).count() > 0
    if is_ajax:
        return jsonify({'ok': True, 'liked': liked, 'likes': post.likes})

    return redirect(url_for('feed.feed', _anchor=f"post-{post_id}"))

@feed_bp.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    if 'user_id' not in session: 
        return redirect(url_for('welcome'))
    from app import Comment, Post, db, notify_mentions, Notification
    
    content = request.form.get('comment_content')
    post = Post.query.get_or_404(post_id)
    
    if not content or not content.strip():
        # For AJAX requests, return JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Comentário não pode estar vazio', 'ok': False}), 400
        # For form submissions, redirect with error
        return redirect(url_for('feed.feed', _anchor=f"post-{post_id}"))
    
    try:
        autor_username = session.get('username')
        user_id = session.get('user_id')
        new_comment = Comment(content=content.strip(), post_id=post_id, username=autor_username, user_id=user_id)
        db.session.add(new_comment)
        
        if post.user_id and post.user_id != session.get('user_id'):
            db.session.add(Notification(user_id=post.user_id, sender_name=session.get('name'), action_type="comentou sua publicação", post_id=post.id))
        
        notify_mentions(content, session.get('name'), post.id)
        db.session.commit()
        
        # For AJAX requests, return JSON success
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'ok': True,
                'comment_id': new_comment.id,
                'message': 'Comentário adicionado com sucesso'
            }), 201
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Erro ao adicionar comentário', 'ok': False}), 500
    
    return redirect(url_for('feed.feed', _anchor=f"post-{post_id}"))

@feed_bp.route('/eventos')
def eventos():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import Event, Notification

    all_events = Event.query.order_by(Event.created_at.desc()).all()
    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template('eventos.html', events=all_events, unread_count=unread)

@feed_bp.route('/criar_evento', methods=['POST'])
def criar_evento():
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import Event, Post, db, uuid, save_and_optimize_image, build_event_post_content, normalize_event_description, parse_event_datetime

    title = request.form.get('title')
    description = normalize_event_description(request.form.get('description'))
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')

    if not (title or '').strip() or not description or not (location or '').strip():
        flash('Preencha todos os campos obrigatorios do evento.')
        return redirect(url_for('feed.eventos'))

    _, datetime_error = parse_event_datetime(date, time)
    if datetime_error:
        flash(datetime_error)
        return redirect(url_for('feed.eventos'))
    
    file = request.files.get('file'); filename = None
    if file and file.filename != '':
        filename_base = str(uuid.uuid4())
        filename = save_and_optimize_image(file, filename_base)

    full_date = f"{date} às {time}"
    new_event = Event(title=title, description=description, event_date=full_date, location=location, media_url=filename, user_id=session['user_id'])
    db.session.add(new_event)
    
    # Criar postagem no feed automaticamente
    event_content = build_event_post_content(title, location, full_date, description, session['username'])
    feed_post = Post(content=event_content, media_url=filename, user_id=session['user_id'], is_anonymous=False)
    db.session.add(feed_post)

    db.session.commit()
    return redirect(url_for('feed.eventos'))


@feed_bp.route('/editar_evento/<int:event_id>', methods=['POST'])
def editar_evento(event_id):
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    from app import Event, db, normalize_event_description, parse_event_datetime, sync_event_feed_post

    event = Event.query.get_or_404(event_id)
    if event.user_id != session.get('user_id') and not session.get('is_admin'):
        return redirect(url_for('feed.eventos'))

    old_title = event.title
    old_location = event.location
    old_event_date = event.event_date
    old_description = event.description


    title = (request.form.get('title') or '').strip()
    description = normalize_event_description(request.form.get('description'))
    date = (request.form.get('date') or '').strip()
    time = (request.form.get('time') or '').strip()
    location = (request.form.get('location') or '').strip()

    if not title or not description or not date or not time or not location:
        flash('Preencha todos os campos obrigatorios do evento.')
        return redirect(url_for('feed.eventos'))

    _, datetime_error = parse_event_datetime(date, time)
    if datetime_error:
        flash(datetime_error)
        return redirect(url_for('feed.eventos'))

    event.title = title[:100]
    event.description = description
    event.location = location[:100]
    event.event_date = f"{date} às {time}"

    sync_event_feed_post(event, old_title, old_location, old_event_date, old_description)
    db.session.commit()
    return redirect(url_for('feed.eventos'))

@feed_bp.route('/excluir_evento/<int:event_id>')
def excluir_evento(event_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    from app import Event, db
    event = Event.query.get_or_404(event_id)
    if event.user_id == session['user_id'] or session.get('is_admin'):
        db.session.delete(event)
        db.session.commit()
    return redirect(url_for('feed.eventos'))

@feed_bp.route('/api/comments/<int:comment_id>/edit', methods=['POST'])
def api_edit_comment(comment_id):
    """API endpoint to edit a comment. Returns JSON response."""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado', 'ok': False}), 401

    from app import Comment, db

    comment = Comment.query.get_or_404(comment_id)

    # Verify permission to edit (author only)
    current_user_id = session.get('user_id')
    comment_user_id = comment.user_id

    # Safe type conversion for comparison
    try:
        current_user_id = int(current_user_id) if current_user_id else None
        comment_user_id = int(comment_user_id) if comment_user_id else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Sem permissão para editar', 'ok': False}), 403

    if not current_user_id or not comment_user_id or comment_user_id != current_user_id:
        return jsonify({'error': 'Sem permissão para editar', 'ok': False}), 403

    # Get new content from JSON payload
    data = request.get_json(silent=True) or {}
    new_content = (data.get('content') or '').strip()

    if not new_content:
        return jsonify({'error': 'Comentário não pode estar vazio', 'ok': False}), 400

    if len(new_content) > 500:
        return jsonify({'error': 'Comentário muito longo (máx 500 caracteres)', 'ok': False}), 400

    # Update comment
    comment.content = new_content
    comment.is_edited = True
    db.session.commit()

    return jsonify({
        'ok': True,
        'comment_id': comment.id,
        'content': comment.content,
        'is_edited': comment.is_edited,
        'message': 'Comentário atualizado com sucesso'
    }), 200

@feed_bp.route('/api/comments/<int:comment_id>/delete', methods=['POST'])
def api_delete_comment(comment_id):
    """API endpoint to delete a comment. Returns JSON response."""
    if 'user_id' not in session:
        return jsonify({'error': 'Não autenticado', 'ok': False}), 401

    from app import Comment, db

    comment = Comment.query.get_or_404(comment_id)

    # Verify permission to delete (author or admin)
    is_author = comment.user_id == session.get('user_id')
    is_admin = session.get('is_admin', False)

    if not (is_author or is_admin):
        return jsonify({'error': 'Sem permissão para deletar', 'ok': False}), 403

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()

    return jsonify({
        'ok': True,
        'comment_id': comment_id,
        'post_id': post_id,
        'message': 'Comentário deletado com sucesso'
    }), 200

# Keep old routes for backwards compatibility (if needed elsewhere)
@feed_bp.route('/editar_comentario/<int:comment_id>', methods=['POST'])
def editar_comentario(comment_id):
    """Legacy route - redirects to feed after editing."""
    if 'user_id' not in session:
        return redirect(url_for('feed.feed'))
    from app import Comment, Post, db

    comment = Comment.query.get_or_404(comment_id)

    # Verify permission to edit (author only)
    current_user_id = session.get('user_id')
    comment_user_id = comment.user_id

    # Safe type conversion for comparison
    try:
        current_user_id = int(current_user_id) if current_user_id else None
        comment_user_id = int(comment_user_id) if comment_user_id else None
    except (TypeError, ValueError):
        flash('Você não tem permissão para editar este comentário.')
        return redirect(url_for('feed.feed'))

    if not current_user_id or not comment_user_id or comment_user_id != current_user_id:
        flash('Você não tem permissão para editar este comentário.')
        return redirect(url_for('feed.feed'))

    content = request.form.get('content', '').strip()
    if not content:
        flash('O comentário não pode estar vazio.')
        return redirect(url_for('feed.feed'))

    comment.content = content
    comment.is_edited = True
    db.session.commit()

    post = Post.query.get(comment.post_id)
    return redirect(url_for('feed.feed', _anchor=f"post-{post.id}"))

@feed_bp.route('/excluir_comentario/<int:comment_id>')
def excluir_comentario(comment_id):
    """Legacy route - redirects to feed after deleting."""
    if 'user_id' not in session:
        return redirect(url_for('feed.feed'))
    from app import Comment, Post, db

    comment = Comment.query.get_or_404(comment_id)

    # Verify permission to delete (author or admin)
    is_author = comment.user_id == session.get('user_id')
    is_admin = session.get('is_admin', False)

    if not (is_author or is_admin):
        flash('Você não tem permissão para deletar este comentário.')
        return redirect(url_for('feed.feed'))

    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()

    return redirect(url_for('feed.feed', _anchor=f"post-{post_id}"))

