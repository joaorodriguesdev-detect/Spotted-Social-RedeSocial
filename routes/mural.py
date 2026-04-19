from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from markupsafe import escape

mural_bp = Blueprint('mural', __name__, url_prefix='/mural')

# Import inside functions to avoid circular imports
def get_db_models():
    from app import db, MuralPost, User, Notification, br_time, create_notification, socketio
    return db, MuralPost, User, Notification, br_time, create_notification, socketio

# List of allowed categories for mural posts
ALLOWED_CATEGORIES = ['Emprego', 'Saúde', 'Geral', 'Educação', 'Moradia', 'Eventos', 'Carona']

def sanitize_input(text):
    """Sanitize user input by escaping HTML special characters."""
    if not text:
        return ''
    # Strip whitespace and limit length
    clean_text = str(text).strip()[:1000]
    # Escape HTML entities
    return escape(clean_text)

@mural_bp.route('/')
def mural_list():
    """Display all mural posts paginated."""
    db, MuralPost, User, Notification, br_time, _, _ = get_db_models()

    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    page = request.args.get('page', 1, type=int)
    category = (request.args.get('category') or 'Todos').strip()

    # Build query
    query = MuralPost.query.order_by(MuralPost.timestamp.desc())

    # Filter by category if specified
    if category != 'Todos' and category in ALLOWED_CATEGORIES:
        query = query.filter_by(category=category)

    # Paginate: 12 posts per page
    pagination = query.paginate(page=page, per_page=12, error_out=False)
    posts = pagination.items

    # Annotate posts with author info
    for post in posts:
        if post.author:
            post.author_name = post.author.name or post.author.username
            post.author_username = post.author.username
            post.author_pic = post.author.profile_pic

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()

    return render_template(
        'mural.html',
        posts=posts,
        pagination=pagination,
        current_category=category if category in ALLOWED_CATEGORIES or category == 'Todos' else 'Todos',
        categories=ALLOWED_CATEGORIES,
        unread_count=unread
    )

@mural_bp.route('/criar', methods=['GET', 'POST'])
def criar_mural_post():
    """Create a new mural post."""
    db, MuralPost, User, Notification, br_time, create_notification, socketio = get_db_models()

    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    if request.method == 'POST':
        # Get and sanitize form inputs
        title = sanitize_input(request.form.get('title', ''))
        content = sanitize_input(request.form.get('content', ''))
        category = (request.form.get('category') or 'Geral').strip()
        contact_info = sanitize_input(request.form.get('contact_info', ''))

        # Validate inputs
        if not title or len(title) < 5:
            flash('Título deve ter pelo menos 5 caracteres.')
            return redirect(url_for('mural.criar_mural_post'))

        if not content or len(content) < 10:
            flash('Descrição deve ter pelo menos 10 caracteres.')
            return redirect(url_for('mural.criar_mural_post'))

        if category not in ALLOWED_CATEGORIES:
            flash('Categoria inválida.')
            return redirect(url_for('mural.criar_mural_post'))

        if not contact_info or len(contact_info) < 5:
            flash('Informação de contato é obrigatória (mínimo 5 caracteres).')
            return redirect(url_for('mural.criar_mural_post'))

        # Create new post
        try:
            post = MuralPost(
                title=title,
                content=content,
                category=category,
                contact_info=contact_info,
                user_id=session.get('user_id'),
                timestamp=br_time()
            )
            db.session.add(post)
            db.session.commit()

            # Get current user name
            current_user = User.query.get(session.get('user_id'))
            username = current_user.username if current_user else 'Usuário'

            # Create notifications for all users
            all_users = User.query.all()
            for user in all_users:
                try:
                    create_notification(
                        user_id=user.id,
                        sender_name=username,
                        action_type=f'Novo anúncio: {title}',
                        post_id=post.id,
                        category='mural'
                    )
                except Exception:
                    # Don't fail if notification creation fails for one user
                    pass

            # Emit a broadcast event to all connected clients
            try:
                socketio.emit('mural:new-post', {
                    'post_id': post.id,
                    'title': title,
                    'category': category,
                    'username': username,
                    'timestamp': post.timestamp.isoformat() if post.timestamp else None
                }, broadcast=True)
            except Exception:
                # Don't fail if socket emit fails
                pass

            flash('Anúncio publicado com sucesso!')
            return redirect(url_for('mural.mural_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao publicar anúncio: {str(e)}')
            return redirect(url_for('mural.criar_mural_post'))

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'mural_criar.html',
        categories=ALLOWED_CATEGORIES,
        unread_count=unread
    )

@mural_bp.route('/<int:post_id>/editar', methods=['GET', 'POST'])
def editar_mural_post(post_id):
    """Edit a mural post (only by author)."""
    db, MuralPost, User, Notification, br_time, _, _ = get_db_models()

    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    post = MuralPost.query.get_or_404(post_id)

    # Check ownership
    if post.user_id != session.get('user_id'):
        flash('Você não tem permissão para editar este anúncio.')
        return redirect(url_for('mural.mural_list'))

    if request.method == 'POST':
        # Get and sanitize form inputs
        title = sanitize_input(request.form.get('title', ''))
        content = sanitize_input(request.form.get('content', ''))
        category = (request.form.get('category') or post.category).strip()
        contact_info = sanitize_input(request.form.get('contact_info', ''))

        # Validate inputs
        if not title or len(title) < 5:
            flash('Título deve ter pelo menos 5 caracteres.')
            return redirect(url_for('mural.editar_mural_post', post_id=post_id))

        if not content or len(content) < 10:
            flash('Descrição deve ter pelo menos 10 caracteres.')
            return redirect(url_for('mural.editar_mural_post', post_id=post_id))

        if category not in ALLOWED_CATEGORIES:
            flash('Categoria inválida.')
            return redirect(url_for('mural.editar_mural_post', post_id=post_id))

        if not contact_info or len(contact_info) < 5:
            flash('Informação de contato é obrigatória (mínimo 5 caracteres).')
            return redirect(url_for('mural.editar_mural_post', post_id=post_id))

        # Update post
        try:
            post.title = title
            post.content = content
            post.category = category
            post.contact_info = contact_info
            db.session.commit()
            flash('Anúncio atualizado com sucesso!')
            return redirect(url_for('mural.mural_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar anúncio: {str(e)}')
            return redirect(url_for('mural.editar_mural_post', post_id=post_id))

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'mural_editar.html',
        post=post,
        categories=ALLOWED_CATEGORIES,
        unread_count=unread
    )

@mural_bp.route('/<int:post_id>/deletar', methods=['POST'])
def deletar_mural_post(post_id):
    """Delete a mural post (only by author or admin)."""
    db, MuralPost, User, Notification, br_time, _, _ = get_db_models()

    if 'user_id' not in session:
        return redirect(url_for('welcome'))

    post = MuralPost.query.get_or_404(post_id)
    user = User.query.get(session.get('user_id'))

    # Check ownership or admin
    if post.user_id != session.get('user_id') and not user.is_admin:
        flash('Você não tem permissão para deletar este anúncio.')
        return redirect(url_for('mural.mural_list'))

    try:
        db.session.delete(post)
        db.session.commit()
        flash('Anúncio deletado com sucesso!')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar anúncio: {str(e)}')

    return redirect(url_for('mural.mural_list'))

@mural_bp.route('/api/search')
def api_search_mural():
    """API endpoint for searching mural posts."""
    db, MuralPost, User, Notification, br_time, _, _ = get_db_models()

    if 'user_id' not in session:
        return jsonify({'error': 'não autenticado'}), 401

    q = (request.args.get('q') or '').strip().lower()
    category = (request.args.get('category') or '').strip()

    if not q:
        return jsonify([])

    query = MuralPost.query

    # Filter by category if specified
    if category and category in ALLOWED_CATEGORIES:
        query = query.filter_by(category=category)

    # Search in title and content
    query = query.filter(
        (MuralPost.title.ilike(f'%{q}%')) |
        (MuralPost.content.ilike(f'%{q}%'))
    ).order_by(MuralPost.timestamp.desc()).limit(20)

    results = query.all()

    return jsonify([{
        'id': post.id,
        'title': post.title,
        'category': post.category,
        'preview': post.content[:100] + ('...' if len(post.content) > 100 else ''),
        'timestamp': post.timestamp.isoformat() if post.timestamp else None
    } for post in results])

