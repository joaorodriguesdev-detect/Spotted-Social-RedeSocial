from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template, session
from flask_socketio import emit, join_room, leave_room
from sqlalchemy import select, and_, or_, func
import re
import uuid
from app import db, User, Conversation, ConversationMember, DirectChatMessage, MessageReaction, Notification, socketio, online_user_connections, GROUP_CHAT_PARTICIPANTS, GROUP_CHAT_ADMINS, followers, get_membership, can_user_access_group_conversation, is_direct_blocked_for_system_admin, is_direct_temporarily_disabled_for_users, is_direct_globally_disabled, conversation_room_name, serialize_group_member, build_members_payload, emit_group_members_updated, emit_group_updated, emit_presence_for_user, create_notification, ensure_group_conversation, get_or_create_dm_conversation, serialize_direct_message, serialize_direct_message_broadcast, get_conversation_pinned_message, get_group_members, can_manage_group, get_latest_message_id, mark_conversation_read, get_unread_message_count, get_direct_unread_total, build_direct_inbox_items, users_follow_each_other

direct_bp = Blueprint('direct', __name__)


@direct_bp.route('/api/users')
def api_users():
    app_mod = _app()
    q = request.args.get('q', '').lower()
    if not q: return jsonify([])
    User = app_mod.User
    users = User.query.filter(User.username.like(f'{q}%'), User.is_admin == False).limit(5).all()
    return jsonify([{'username': u.username, 'name': u.name} for u in users])


@direct_bp.route('/api/direct/users')
def api_direct_users():
    app_mod = _app()
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if app_mod.is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    q = (request.args.get('q') or '').strip().lower().replace('@', '')
    current_user_id = session.get('user_id')
    User = app_mod.User
    current_user = User.query.get(current_user_id)

    query = User.query.filter(
        User.id != current_user_id,
        User.is_admin.is_(False)
    )

    if q:
        query = query.filter(
            or_(
                User.username.ilike(f'%{q}%'),
                User.name.ilike(f'%{q}%')
            )
        )

    users = []
    if current_user:
        try:
            followers = app_mod.followers
            mutual_a = select([1]).where(and_(followers.c.follower_id == current_user_id, followers.c.followed_id == User.id)).exists()
            mutual_b = select([1]).where(and_(followers.c.follower_id == User.id, followers.c.followed_id == current_user_id)).exists()
            users = query.filter(mutual_a, mutual_b).order_by(User.username.asc()).limit(20).all()
        except Exception:
            users = query.order_by(User.username.asc()).limit(50).all()
            users = [user for user in users if app_mod.users_follow_each_other(current_user, user)]
    else:
        users = []

    return jsonify({'users': [
        {
            'username': user.username,
            'name': user.name,
            'profile_pic': user.profile_pic
        }
        for user in users
    ]})


@direct_bp.route('/api/direct/conversations/start', methods=['POST'])
def api_direct_start_conversation():
    app_mod = _app()
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if app_mod.is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip().lower().replace('@', '')
    if not username:
        return jsonify({'error': 'usuario invalido'}), 400

    current_user_id = session.get('user_id')
    User = app_mod.User
    target_user = User.query.filter_by(username=username).first()
    if not target_user:
        return jsonify({'error': 'usuario nao encontrado'}), 404
    if target_user.id == current_user_id or target_user.is_admin:
        return jsonify({'error': 'nao permitido'}), 400

    app_mod.get_or_create_dm_conversation(current_user_id, target_user.id)
    return jsonify({'ok': True, 'url': url_for('direct_conversation', username=target_user.username)})


def generate_group_slug(title):
    app_mod = _app()
    Conversation = app_mod.Conversation
    base = re.sub(r'[^a-z0-9]+', '-', (title or '').strip().lower()).strip('-')
    if not base:
        base = f'grupo-{uuid.uuid4().hex[:6]}'

    slug = base[:72]
    if not Conversation.query.filter_by(slug=slug).first():
        return slug

    while True:
        suffix = uuid.uuid4().hex[:6]
        candidate = f"{slug[:65]}-{suffix}"
        if not Conversation.query.filter_by(slug=candidate).first():
            return candidate


@direct_bp.route('/api/direct/groups', methods=['POST'])
def api_direct_create_group():
    app_mod = _app()
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if app_mod.is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'nome do grupo e obrigatorio'}), 400

    current_user_id = session.get('user_id')
    raw_usernames = payload.get('usernames') or []
    if not isinstance(raw_usernames, list):
        raw_usernames = []

    normalized_usernames = []
    seen = set()
    for raw_username in raw_usernames:
        clean_username = (raw_username or '').strip().lower().replace('@', '')
        if not clean_username or clean_username in seen:
            continue
        seen.add(clean_username)
        normalized_usernames.append(clean_username)

    User = app_mod.User
    Conversation = app_mod.Conversation
    ConversationMember = app_mod.ConversationMember
    db = app_mod.db

    current_user = User.query.get(current_user_id)
    if not current_user:
        return jsonify({'error': 'usuario invalido'}), 400

    selected_users = []
    if normalized_usernames:
        selected_users = User.query.filter(
            User.username.in_(normalized_usernames),
            User.id != current_user_id,
            User.is_admin.is_(False)
        ).all()

    selected_users = [user for user in selected_users if app_mod.users_follow_each_other(current_user, user)]

    if not selected_users:
        return jsonify({'error': 'selecione ao menos um integrante valido para criar o grupo'}), 400

    conversation = Conversation(
        slug=generate_group_slug(title),
        title=title[:80],
        is_group=True
    )
    db.session.add(conversation)
    db.session.flush()

    db.session.add(ConversationMember(
        conversation_id=conversation.id,
        user_id=current_user_id,
        is_admin=True
    ))

    for user in selected_users:
        db.session.add(ConversationMember(
            conversation_id=conversation.id,
            user_id=user.id,
            is_admin=False
        ))

    db.session.commit()
    app_mod.emit_group_members_updated(conversation.id)
    return jsonify({'ok': True, 'url': url_for('direct_conversation', username=conversation.slug)})


@direct_bp.route('/direct')
def direct():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    if is_direct_blocked_for_system_admin():
        flash('Conta administradora do sistema nao possui acesso ao Direct.')
        return redirect(url_for('feed'))

    current_filter = (request.args.get('filter') or 'all').strip().lower()
    if current_filter not in {'all', 'unread'}:
        current_filter = 'all'
    search_query = (request.args.get('q') or '').strip().lower()

    current_user_id = session.get('user_id')
    conversations = build_direct_inbox_items(
        current_user_id=current_user_id,
        current_filter=current_filter,
        search_query=search_query,
        for_api=False
    )

    unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
    return render_template(
        'direct.html',
        unread_count=unread,
        conversations=conversations,
        current_filter=current_filter,
        search_query=search_query
        , direct_enabled=app.config.get('DIRECT_ENABLED', True)
    )


@direct_bp.route('/api/direct/conversations')
def api_direct_conversations():
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_filter = (request.args.get('filter') or 'all').strip().lower()
    if current_filter not in {'all', 'unread'}:
        current_filter = 'all'
    search_query = (request.args.get('q') or '').strip().lower()

    payload = build_direct_inbox_items(
        current_user_id=session.get('user_id'),
        current_filter=current_filter,
        search_query=search_query,
        for_api=True
    )
    return jsonify(payload)


@direct_bp.route('/api/direct/conversations/<int:conversation_id>/messages')
def api_direct_messages(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    messages = DirectChatMessage.query.filter_by(conversation_id=conversation_id).order_by(DirectChatMessage.id.asc()).all()
    mark_conversation_read(conversation_id, current_user_id)
    return jsonify({
        'messages': [serialize_direct_message(msg, current_user_id) for msg in messages],
        'pinned_message': get_conversation_pinned_message(conversation_id, current_user_id)
    })


@direct_bp.route('/api/direct/conversations/<int:conversation_id>/read', methods=['POST'])
def api_direct_mark_read(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    mark_conversation_read(conversation_id, current_user_id)
    return jsonify({'ok': True})


@direct_bp.route('/api/direct/conversations/<int:conversation_id>/pin', methods=['PATCH'])
def api_direct_pin_message(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403
    if not conversation:
        return jsonify({'error': 'conversa nao encontrada'}), 404

    payload = request.get_json(silent=True) or {}
    raw_message_id = payload.get('message_id')
    pinned_payload = None

    if raw_message_id is None:
        conversation.pinned_message_id = None
    else:
        try:
            message_id = int(raw_message_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'mensagem invalida'}), 400

        message = DirectChatMessage.query.filter_by(id=message_id, conversation_id=conversation_id).first()
        if not message:
            return jsonify({'error': 'mensagem nao encontrada'}), 404
        conversation.pinned_message_id = message.id
        pinned_payload = serialize_direct_message(message, current_user_id)

    db.session.commit()

    if pinned_payload is None:
        pinned_payload = get_conversation_pinned_message(conversation_id, current_user_id)

    socketio.emit('direct:pinned-updated', {
        'conversation_id': conversation_id,
        'pinned_message': pinned_payload
    }, room=conversation_room_name(conversation_id))
    return jsonify({'ok': True, 'pinned_message': pinned_payload})


@direct_bp.route('/api/direct/conversations/<int:conversation_id>/members')
def api_direct_members(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    conversation = Conversation.query.get_or_404(conversation_id)
    if not conversation.is_group:
        return jsonify({'error': 'conversa nao e grupo'}), 400

    return jsonify({'members': build_members_payload(conversation_id)})


@direct_bp.route('/api/direct/conversations/<int:conversation_id>/messages', methods=['POST'])
def api_direct_send_message(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'nao autenticado'}), 401
    if is_direct_blocked_for_system_admin():
        return jsonify({'error': 'acesso negado'}), 403

    current_user_id = session.get('user_id')
    membership = get_membership(conversation_id, current_user_id)
    current_user = User.query.get(current_user_id)
    conversation = Conversation.query.get(conversation_id)
    if not membership or not can_user_access_group_conversation(conversation, current_user):
        return jsonify({'error': 'acesso negado'}), 403

    payload = request.get_json(silent=True) or {}
    content = (payload.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'mensagem vazia'}), 400
    if len(content) > 500:
        return jsonify({'error': 'mensagem muito longa'}), 400

    import time
    t0 = time.time()
    message = DirectChatMessage(conversation_id=conversation_id, sender_id=current_user_id, content=content)
        from flask import Blueprint, request, redirect, url_for, flash, jsonify, render_template, session
        from flask_socketio import emit, join_room, leave_room
        from sqlalchemy import select, and_, or_, func
        import re
        import uuid
        from app import db, User, Conversation, ConversationMember, DirectChatMessage, MessageReaction, Notification, socketio, online_user_connections, GROUP_CHAT_PARTICIPANTS, GROUP_CHAT_ADMINS, followers, get_membership, can_user_access_group_conversation, is_direct_blocked_for_system_admin, is_direct_temporarily_disabled_for_users, is_direct_globally_disabled, conversation_room_name, serialize_group_member, build_members_payload, emit_group_members_updated, emit_group_updated, emit_presence_for_user, create_notification, ensure_group_conversation, get_or_create_dm_conversation, serialize_direct_message, serialize_direct_message_broadcast, get_conversation_pinned_message, get_group_members, can_manage_group, get_latest_message_id, mark_conversation_read, get_unread_message_count, get_direct_unread_total, build_direct_inbox_items, users_follow_each_other

        direct_bp = Blueprint('direct', __name__)

        @direct_bp.route('/api/users')
        def api_users():
            q = request.args.get('q', '').lower()
            if not q: return jsonify([])
            users = User.query.filter(User.username.like(f'{q}%'), User.is_admin == False).limit(5).all()
            return jsonify([{'username': u.username, 'name': u.name} for u in users])


        @direct_bp.route('/api/direct/users')
        def api_direct_users():
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            q = (request.args.get('q') or '').strip().lower().replace('@', '')
            current_user_id = session.get('user_id')
            current_user = User.query.get(current_user_id)

            query = User.query.filter(
                User.id != current_user_id,
                User.is_admin.is_(False)
            )

            if q:
                query = query.filter(
                    or_(
                        User.username.ilike(f'%{q}%'),
                        User.name.ilike(f'%{q}%')
                    )
                )

            # Apply mutual-follow filter at the database level so the LIMIT applies to
            # already-filtered results. This prevents returning non-mutual users when
            # the current user follows nobody.
            users = []
            if current_user:
                try:
                    mutual_a = select([1]).where(and_(followers.c.follower_id == current_user_id, followers.c.followed_id == User.id)).exists()
                    mutual_b = select([1]).where(and_(followers.c.follower_id == User.id, followers.c.followed_id == current_user_id)).exists()
                    users = query.filter(mutual_a, mutual_b).order_by(User.username.asc()).limit(20).all()
                except Exception:
                    # Fallback to previous Python-level filtering in case the SQL EXISTS
                    # expression isn't supported in this environment/version.
                    users = query.order_by(User.username.asc()).limit(50).all()
                    users = [user for user in users if users_follow_each_other(current_user, user)]
            else:
                users = []

            return jsonify({'users': [
                {
                    'username': user.username,
                    'name': user.name,
                    'profile_pic': user.profile_pic
                }
                for user in users
            ]})


        @direct_bp.route('/api/direct/conversations/start', methods=['POST'])
        def api_direct_start_conversation():
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            payload = request.get_json(silent=True) or {}
            username = (payload.get('username') or '').strip().lower().replace('@', '')
            if not username:
                return jsonify({'error': 'usuario invalido'}), 400

            current_user_id = session.get('user_id')
            target_user = User.query.filter_by(username=username).first()
            if not target_user:
                return jsonify({'error': 'usuario nao encontrado'}), 404
            if target_user.id == current_user_id or target_user.is_admin:
                return jsonify({'error': 'nao permitido'}), 400

            get_or_create_dm_conversation(current_user_id, target_user.id)
            return jsonify({'ok': True, 'url': url_for('direct_conversation', username=target_user.username)})


        def generate_group_slug(title):
            base = re.sub(r'[^a-z0-9]+', '-', (title or '').strip().lower()).strip('-')
            if not base:
                base = f'grupo-{uuid.uuid4().hex[:6]}'

            slug = base[:72]
            if not Conversation.query.filter_by(slug=slug).first():
                return slug

            while True:
                suffix = uuid.uuid4().hex[:6]
                candidate = f"{slug[:65]}-{suffix}"
                if not Conversation.query.filter_by(slug=candidate).first():
                    return candidate


        @direct_bp.route('/api/direct/groups', methods=['POST'])
        def api_direct_create_group():
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            payload = request.get_json(silent=True) or {}
            title = (payload.get('title') or '').strip()
            if not title:
                return jsonify({'error': 'nome do grupo e obrigatorio'}), 400

            current_user_id = session.get('user_id')
            raw_usernames = payload.get('usernames') or []
            if not isinstance(raw_usernames, list):
                raw_usernames = []

            normalized_usernames = []
            seen = set()
            for raw_username in raw_usernames:
                clean_username = (raw_username or '').strip().lower().replace('@', '')
                if not clean_username or clean_username in seen:
                    continue
                seen.add(clean_username)
                normalized_usernames.append(clean_username)

            current_user = User.query.get(current_user_id)
            if not current_user:
                return jsonify({'error': 'usuario invalido'}), 400

            selected_users = []
            if normalized_usernames:
                selected_users = User.query.filter(
                    User.username.in_(normalized_usernames),
                    User.id != current_user_id,
                    User.is_admin.is_(False)
                ).all()

            selected_users = [user for user in selected_users if users_follow_each_other(current_user, user)]

            if not selected_users:
                return jsonify({'error': 'selecione ao menos um integrante valido para criar o grupo'}), 400

            conversation = Conversation(
                slug=generate_group_slug(title),
                title=title[:80],
                is_group=True
            )
            db.session.add(conversation)
            db.session.flush()

            db.session.add(ConversationMember(
                conversation_id=conversation.id,
                user_id=current_user_id,
                is_admin=True
            ))

            for user in selected_users:
                db.session.add(ConversationMember(
                    conversation_id=conversation.id,
                    user_id=user.id,
                    is_admin=False
                ))

            db.session.commit()
            emit_group_members_updated(conversation.id)
            return jsonify({'ok': True, 'url': url_for('direct_conversation', username=conversation.slug)})


        @direct_bp.route('/direct')
        def direct():
            if 'user_id' not in session:
                return redirect(url_for('welcome'))
            if is_direct_blocked_for_system_admin():
                flash('Conta administradora do sistema nao possui acesso ao Direct.')
                return redirect(url_for('feed'))

            current_filter = (request.args.get('filter') or 'all').strip().lower()
            if current_filter not in {'all', 'unread'}:
                current_filter = 'all'
            search_query = (request.args.get('q') or '').strip().lower()

            current_user_id = session.get('user_id')
            conversations = build_direct_inbox_items(
                current_user_id=current_user_id,
                current_filter=current_filter,
                search_query=search_query,
                for_api=False
            )

            unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
            return render_template(
                'direct.html',
                unread_count=unread,
                conversations=conversations,
                current_filter=current_filter,
                search_query=search_query
                , direct_enabled=app.config.get('DIRECT_ENABLED', True)
            )


        @direct_bp.route('/api/direct/conversations')
        def api_direct_conversations():
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_filter = (request.args.get('filter') or 'all').strip().lower()
            if current_filter not in {'all', 'unread'}:
                current_filter = 'all'
            search_query = (request.args.get('q') or '').strip().lower()

            payload = build_direct_inbox_items(
                current_user_id=session.get('user_id'),
                current_filter=current_filter,
                search_query=search_query,
                for_api=True
            )
            return jsonify(payload)


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/messages')
        def api_direct_messages(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            membership = get_membership(conversation_id, current_user_id)
            current_user = User.query.get(current_user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, current_user):
                return jsonify({'error': 'acesso negado'}), 403

            messages = DirectChatMessage.query.filter_by(conversation_id=conversation_id).order_by(DirectChatMessage.id.asc()).all()
            mark_conversation_read(conversation_id, current_user_id)
            return jsonify({
                'messages': [serialize_direct_message(msg, current_user_id) for msg in messages],
                'pinned_message': get_conversation_pinned_message(conversation_id, current_user_id)
            })


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/read', methods=['POST'])
        def api_direct_mark_read(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            membership = get_membership(conversation_id, current_user_id)
            current_user = User.query.get(current_user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, current_user):
                return jsonify({'error': 'acesso negado'}), 403

            mark_conversation_read(conversation_id, current_user_id)
            return jsonify({'ok': True})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/pin', methods=['PATCH'])
        def api_direct_pin_message(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            membership = get_membership(conversation_id, current_user_id)
            current_user = User.query.get(current_user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, current_user):
                return jsonify({'error': 'acesso negado'}), 403
            if not conversation:
                return jsonify({'error': 'conversa nao encontrada'}), 404

            payload = request.get_json(silent=True) or {}
            raw_message_id = payload.get('message_id')
            pinned_payload = None

            if raw_message_id is None:
                conversation.pinned_message_id = None
            else:
                try:
                    message_id = int(raw_message_id)
                except (TypeError, ValueError):
                    return jsonify({'error': 'mensagem invalida'}), 400

                message = DirectChatMessage.query.filter_by(id=message_id, conversation_id=conversation_id).first()
                if not message:
                    return jsonify({'error': 'mensagem nao encontrada'}), 404
                conversation.pinned_message_id = message.id
                pinned_payload = serialize_direct_message(message, current_user_id)

            db.session.commit()

            if pinned_payload is None:
                pinned_payload = get_conversation_pinned_message(conversation_id, current_user_id)

            socketio.emit('direct:pinned-updated', {
                'conversation_id': conversation_id,
                'pinned_message': pinned_payload
            }, room=conversation_room_name(conversation_id))
            return jsonify({'ok': True, 'pinned_message': pinned_payload})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/members')
        def api_direct_members(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            membership = get_membership(conversation_id, current_user_id)
            current_user = User.query.get(current_user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, current_user):
                return jsonify({'error': 'acesso negado'}), 403

            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400

            return jsonify({'members': build_members_payload(conversation_id)})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/messages', methods=['POST'])
        def api_direct_send_message(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            membership = get_membership(conversation_id, current_user_id)
            current_user = User.query.get(current_user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, current_user):
                return jsonify({'error': 'acesso negado'}), 403

            payload = request.get_json(silent=True) or {}
            content = (payload.get('content') or '').strip()
            if not content:
                return jsonify({'error': 'mensagem vazia'}), 400
            if len(content) > 500:
                return jsonify({'error': 'mensagem muito longa'}), 400

            import time
            t0 = time.time()
            message = DirectChatMessage(conversation_id=conversation_id, sender_id=current_user_id, content=content)
            db.session.add(message)
            db.session.flush()

            sender_user = User.query.get(current_user_id)
            sender_label = sender_user.username if sender_user else (session.get('username') or 'usuario')
            recipients = ConversationMember.query.filter(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id != current_user_id
            ).all()

            # Batch notifications to avoid commit per-recipient (performance improvement)
            pending_notifs = []
            for recipient in recipients:
                pending_notifs.append(Notification(
                    user_id=recipient.user_id,
                    sender_name=sender_label,
                    action_type='enviou uma mensagem no DM',
                    category='direct'
                ))
                db.session.add(pending_notifs[-1])

            sender_membership = get_membership(conversation_id, current_user_id)
            if sender_membership:
                sender_membership.last_read_message_id = message.id

            db_commit_start = time.time()
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                app.logger.exception('Failed to commit direct message and notifications')
                return jsonify({'error': 'falha ao enviar mensagem'}), 500
            db_commit_end = time.time()

            serialized = serialize_direct_message(message, current_user_id)

            # Emit message and notifications asynchronously so the request doesn't block on socket I/O
            try:
                # Broadcast message to conversation room in background
                def _emit_message(payload, room):
                    try:
                        socketio.emit('direct:message', payload, room=room)
                    except Exception:
                        app.logger.exception('Failed to emit direct:message')

                socketio.start_background_task(_emit_message, serialize_direct_message_broadcast(message), conversation_room_name(conversation_id))

                # Emit notification:new for each created notification in background
                def _emit_notifications(notifs):
                    for n in notifs:
                        try:
                            payload = {
                                'id': n.id,
                                'user_id': n.user_id,
                                'sender_name': n.sender_name,
                                'action_type': n.action_type,
                                'post_id': n.post_id,
                                'is_read': n.is_read,
                                'category': n.category,
                                'timestamp': n.timestamp.isoformat() if n.timestamp else None
                            }
                            socketio.emit('notification:new', payload, room=f'user:{n.user_id}')
                        except Exception:
                            app.logger.exception('Failed to emit notification for user %s', getattr(n, 'user_id', None))

                socketio.start_background_task(_emit_notifications, pending_notifs)
            except Exception:
                app.logger.exception('Failed to start background emit tasks')

            socketio_emit_end = time.time()
            t1 = time.time()
            app.logger.info(f"[PERF] POST /api/direct/conversations/{conversation_id}/messages total: {(t1-t0)*1000:.1f}ms | commit: {(db_commit_end-db_commit_start)*1000:.1f}ms | socketio-bg: {(socketio_emit_end-db_commit_end)*1000:.1f}ms")
            return jsonify({'message': serialized}), 201


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/group', methods=['PATCH'])
        def api_direct_update_group(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400
            if not can_manage_group(conversation_id, current_user_id):
                return jsonify({'error': 'apenas administrador do grupo pode editar o grupo'}), 403

            payload = request.get_json(silent=True) or {}
            title = payload.get('title')
            if title is not None:
                clean_title = (title or '').strip()
                if not clean_title:
                    return jsonify({'error': 'nome do grupo vazio'}), 400
                conversation.title = clean_title[:80]

            group_photo = payload.get('group_photo')
            if group_photo is not None:
                conversation.group_photo = (group_photo or '').strip() or None

            db.session.commit()
            emit_group_updated(conversation)
            return jsonify({'ok': True, 'title': conversation.title, 'group_photo': conversation.group_photo})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/members', methods=['POST'])
        def api_direct_add_member(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400
            if not can_manage_group(conversation_id, current_user_id):
                return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

            payload = request.get_json(silent=True) or {}
            username = (payload.get('username') or '').strip().lower().replace('@', '')
            if not username:
                return jsonify({'error': 'usuario invalido'}), 400

            current_user = User.query.get(current_user_id)
            user = User.query.filter_by(username=username).first()
            if not user:
                return jsonify({'error': 'usuario nao encontrado'}), 404
            if get_membership(conversation_id, user.id):
                return jsonify({'error': 'usuario ja esta no grupo'}), 400
            if not users_follow_each_other(current_user, user):
                return jsonify({'error': 'Para adicionar alguém ao grupo, é necessário que ambos se sigam mutuamente.'}), 400

            db.session.add(ConversationMember(conversation_id=conversation_id, user_id=user.id, is_admin=False))
            db.session.commit()
            emit_group_members_updated(conversation_id)
            # Notify the added user in realtime
            try:
                create_notification(user_id=user.id, sender_name=current_user.username, action_type='foi adicionado ao grupo', category='group')
            except Exception:
                pass
            return jsonify({'ok': True, 'username': user.username}), 201


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/members/<username>', methods=['DELETE'])
        def api_direct_remove_member(conversation_id, username):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400
            if not can_manage_group(conversation_id, current_user_id):
                return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

            target_user = User.query.filter_by(username=(username or '').strip().lower()).first()
            if not target_user:
                return jsonify({'error': 'usuario nao encontrado'}), 404
            if target_user.id == current_user_id:
                return jsonify({'error': 'use a opcao sair do grupo para remover a si mesmo'}), 400

            membership = get_membership(conversation_id, target_user.id)
            if not membership:
                return jsonify({'error': 'usuario nao esta no grupo'}), 404

            if membership.is_admin:
                admin_count = ConversationMember.query.filter_by(conversation_id=conversation_id, is_admin=True).count()
                if admin_count <= 1:
                    return jsonify({'error': 'o grupo precisa de ao menos um administrador'}), 400

            db.session.delete(membership)
            db.session.commit()
            emit_group_members_updated(conversation_id)
            # Notify the removed user
            try:
                create_notification(user_id=target_user.id, sender_name=User.query.get(current_user_id).username, action_type='foi removido do grupo', category='group')
            except Exception:
                pass
            return jsonify({'ok': True})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/leave', methods=['POST'])
        def api_direct_leave_group(conversation_id):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400

            membership = get_membership(conversation_id, current_user_id)
            if not membership:
                return jsonify({'error': 'usuario nao esta no grupo'}), 404

            other_members = ConversationMember.query.filter(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id != current_user_id
            ).order_by(ConversationMember.joined_at.asc(), ConversationMember.id.asc()).all()

            if membership.is_admin:
                has_other_admin = any(member.is_admin for member in other_members)
                if not has_other_admin and other_members:
                    other_members[0].is_admin = True

            db.session.delete(membership)

            if not other_members:
                db.session.delete(conversation)
                db.session.commit()
                return jsonify({'ok': True, 'redirect_url': url_for('direct')})

            db.session.commit()
            emit_group_members_updated(conversation_id)
            # Notify remaining members that this user left (batch notifications)
            try:
                leaving_user = User.query.get(current_user_id)
                for m in other_members:
                    # Add notifications to the session without committing each time
                    create_notification(user_id=m.user_id, sender_name=leaving_user.username if leaving_user else '', action_type='saiu do grupo', category='group', commit=False)
                # commit the pending notifications
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
                # Non-fatal: ignore notification failures
                pass
            return jsonify({'ok': True, 'redirect_url': url_for('direct')})


        @direct_bp.route('/api/direct/conversations/<int:conversation_id>/members/<username>/admin', methods=['PATCH'])
        def api_direct_set_member_admin(conversation_id, username):
            if 'user_id' not in session:
                return jsonify({'error': 'nao autenticado'}), 401
            if is_direct_blocked_for_system_admin():
                return jsonify({'error': 'acesso negado'}), 403

            current_user_id = session.get('user_id')
            conversation = Conversation.query.get_or_404(conversation_id)
            if not conversation.is_group:
                return jsonify({'error': 'conversa nao e grupo'}), 400
            if not can_manage_group(conversation_id, current_user_id):
                return jsonify({'error': 'apenas administrador do grupo pode gerenciar membros'}), 403

            target_user = User.query.filter_by(username=(username or '').strip().lower()).first()
            if not target_user:
                return jsonify({'error': 'usuario nao encontrado'}), 404

            membership = get_membership(conversation_id, target_user.id)
            if not membership:
                return jsonify({'error': 'usuario nao esta no grupo'}), 404

            payload = request.get_json(silent=True) or {}
            next_is_admin = bool(payload.get('is_admin'))

            if membership.is_admin and not next_is_admin:
                admin_count = ConversationMember.query.filter_by(conversation_id=conversation_id, is_admin=True).count()
                if admin_count <= 1:
                    return jsonify({'error': 'o grupo precisa de ao menos um administrador'}), 400

            membership.is_admin = next_is_admin
            db.session.commit()
            emit_group_members_updated(conversation_id)
            return jsonify({'ok': True, 'username': target_user.username, 'is_admin': membership.is_admin})

        @direct_bp.route('/direct/conversa/<username>')
        def direct_conversation(username):
            if 'user_id' not in session:
                return redirect(url_for('welcome'))
            if is_direct_blocked_for_system_admin():
                flash('Conta administradora do sistema nao possui acesso ao Direct.')
                return redirect(url_for('feed'))

            import time
            t0 = time.time()
            clean_username = (username or '').strip().lower()
            if not clean_username:
                return redirect(url_for('direct'))

            # Canonical URL: conversation mode is resolved server-side, not via query params.
            if request.args:
                return redirect(url_for('direct_conversation', username=clean_username), code=302)

            current_user = User.query.get(session.get('user_id'))
            if not current_user:
                session.clear()
                return redirect(url_for('welcome'))

            group_conversation = ensure_group_conversation(clean_username)
            is_group_chat = bool(group_conversation)
            current_username = (session.get('username') or '').strip().lower()

            if is_group_chat:
                conversation = group_conversation
                membership = get_membership(conversation.id, current_user.id)
                if not membership or not can_user_access_group_conversation(conversation, current_user):
                    flash('Voce nao participa deste grupo.')
                    return redirect(url_for('direct'))
                is_group_admin = bool(membership.is_admin)
                target_username = conversation.title or conversation.slug or clean_username
                creator_membership = ConversationMember.query.filter_by(conversation_id=conversation.id).order_by(
                    ConversationMember.joined_at.asc(),
                    ConversationMember.id.asc()
                ).first()
                group_creator_username = creator_membership.user.username if creator_membership and creator_membership.user else ''
            else:
                target_user = User.query.filter_by(username=clean_username).first()
                if not target_user:
                    flash('Conversa nao encontrada.')
                    return redirect(url_for('direct'))
                conversation = get_or_create_dm_conversation(current_user.id, target_user.id)
                is_group_admin = False
                target_username = target_user.username
                group_creator_username = ''

            target_initial = target_username[0].upper() if target_username else 'U'

            # Opening the conversation marks all current messages as read for this user.
            mark_conversation_read(conversation.id, current_user.id)

            members = get_group_members(conversation.id)
            participant_usernames = [member.user.username for member in members if member.user]

            participant_cards = []
            for member in members:
                user_obj = member.user
                if not user_obj:
                    continue
                participant_cards.append({
                    'username': user_obj.username,
                    'profile_pic': user_obj.profile_pic if user_obj else None,
                    'is_admin': bool(member.is_admin)
                })

            unread = Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).count()
            resp = render_template(
                'direct_conversation.html',
                unread_count=unread,
                conversation_id=conversation.id,
                current_user_id=current_user.id,
                target_username=target_username,
                target_initial=target_initial,
                is_group_chat=is_group_chat,
                is_group_admin=is_group_admin,
                group_creator_username=group_creator_username,
                participant_usernames=participant_usernames,
                participant_cards=participant_cards
                , direct_enabled=app.config.get('DIRECT_ENABLED', True)
            )
            t1 = time.time()
            print(f"[PERF] /direct/conversa/{{username}} total: {{(t1-t0)*1000:.1f}}ms")
            return resp
            # NOTE: render_template already returns the response above; ensure direct_enabled passed via context

        @socketio.on('connect')
        def handle_socket_connect():
            user_id = session.get('user_id')
            # Deny socket connections when Direct is globally disabled, or when the
            # session is invalid or access is blocked by maintenance/admin rules.
            if (not user_id
                    or is_direct_globally_disabled()
                    or is_direct_blocked_for_system_admin()
                    or is_direct_temporarily_disabled_for_users()):
                return False

            online_user_connections[user_id] = online_user_connections.get(user_id, 0) + 1
            if online_user_connections[user_id] == 1:
                user = User.query.get(user_id)
                emit_presence_for_user(user, True)
            # Join a personal room so we can push user-specific notifications
            try:
                join_room(f'user:{user_id}')
            except Exception:
                pass
            emit('direct:connected', {'ok': True})


        @socketio.on('disconnect')
        def handle_socket_disconnect():
            user_id = session.get('user_id')
            if not user_id:
                return
            current = online_user_connections.get(user_id, 0)
            if current <= 1:
                online_user_connections.pop(user_id, None)
                user = User.query.get(user_id)
                emit_presence_for_user(user, False)
            else:
                online_user_connections[user_id] = current - 1


        @socketio.on('direct:join')
        def handle_direct_join(payload):
            user_id = session.get('user_id')
            if (not user_id
                    or is_direct_globally_disabled()
                    or is_direct_blocked_for_system_admin()
                    or is_direct_temporarily_disabled_for_users()):
                emit('direct:error', {'error': 'acesso negado'})
                return

            data = payload or {}
            try:
                conversation_id = int(data.get('conversation_id'))
            except (TypeError, ValueError):
                emit('direct:error', {'error': 'conversa invalida'})
                return

            membership = get_membership(conversation_id, user_id)
            user = User.query.get(user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, user):
                emit('direct:error', {'error': 'acesso negado'})
                return

            room = conversation_room_name(conversation_id)
            join_room(room)
            emit('direct:joined', {'conversation_id': conversation_id})


        @socketio.on('direct:leave')
        def handle_direct_leave(payload):
            # If Direct is globally disabled there's nothing to do here.
            if is_direct_globally_disabled():
                return

            data = payload or {}
            try:
                conversation_id = int(data.get('conversation_id'))
            except (TypeError, ValueError):
                return
            leave_room(conversation_room_name(conversation_id))


        @socketio.on('direct:typing')
        def handle_direct_typing(payload):
            user_id = session.get('user_id')
            if (not user_id
                    or is_direct_globally_disabled()
                    or is_direct_blocked_for_system_admin()
                    or is_direct_temporarily_disabled_for_users()):
                return

            data = payload or {}
            try:
                conversation_id = int(data.get('conversation_id'))
            except (TypeError, ValueError):
                return

            membership = get_membership(conversation_id, user_id)
            user = User.query.get(user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, user):
                return

            if not user:
                return

            socketio.emit('direct:typing', {
                'conversation_id': conversation_id,
                'username': user.username,
                'is_typing': bool(data.get('is_typing'))
            }, room=conversation_room_name(conversation_id))


        def get_message_reaction_summary(message_id):
            rows = db.session.query(MessageReaction.reaction, func.count(MessageReaction.id)).filter(MessageReaction.message_id == message_id).group_by(MessageReaction.reaction).all()
            reactions = {r[0]: r[1] for r in rows}
            reactors = {}
            for reaction in reactions.keys():
                users = db.session.query(User.username).join(MessageReaction, User.id == MessageReaction.user_id).filter(MessageReaction.message_id == message_id, MessageReaction.reaction == reaction).all()
                reactors[reaction] = [u[0] for u in users]
            return {'reactions': reactions, 'reactors': reactors}


        @socketio.on('direct:react')
        def handle_direct_react(payload):
            user_id = session.get('user_id')
            if (not user_id
                    or is_direct_globally_disabled()
                    or is_direct_blocked_for_system_admin()
                    or is_direct_temporarily_disabled_for_users()):
                emit('direct:error', {'error': 'acesso negado'})
                return

            data = payload or {}
            try:
                conversation_id = int(data.get('conversation_id'))
                message_id = int(data.get('message_id'))
            except (TypeError, ValueError):
                emit('direct:error', {'error': 'dados inválidos'})
                return
            reaction = (data.get('reaction') or '').strip()
            if not reaction:
                emit('direct:error', {'error': 'reação invalida'})
                return

            membership = get_membership(conversation_id, user_id)
            user = User.query.get(user_id)
            conversation = Conversation.query.get(conversation_id)
            if not membership or not can_user_access_group_conversation(conversation, user):
                emit('direct:error', {'error': 'acesso negado'})
                return

            message = DirectChatMessage.query.get(message_id)
            if not message or message.conversation_id != conversation_id:
                emit('direct:error', {'error': 'mensagem nao encontrada'})
                return

            try:
                existing = MessageReaction.query.filter_by(message_id=message_id, user_id=user_id).first()
                if existing and existing.reaction == reaction:
                    db.session.delete(existing)
                elif existing:
                    existing.reaction = reaction
                else:
                    db.session.add(MessageReaction(message_id=message_id, user_id=user_id, reaction=reaction))
                db.session.commit()
            except Exception:
                db.session.rollback()
                emit('direct:error', {'error': 'falha ao registrar reacao'})
                return

            summary = get_message_reaction_summary(message_id)
            socketio.emit('direct:reaction-updated', {
                'conversation_id': conversation_id,
                'message_id': message_id,
                'reactions': summary['reactions'],
                'reactors': summary['reactors']
            }, room=conversation_room_name(conversation_id))
