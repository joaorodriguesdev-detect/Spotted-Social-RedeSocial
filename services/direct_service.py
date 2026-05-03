from datetime import datetime
from flask import current_app
from sqlalchemy import func

from extensions import socketio
from models import (
    Conversation,
    ConversationMember,
    DirectChatMessage,
    MessageReaction,
    User,
    db,
)

GROUP_CHAT_PARTICIPANTS = {}

GROUP_CHAT_ADMINS = {}


def is_direct_blocked_for_system_admin():
    return False


def is_direct_temporarily_disabled_for_users():
    return False


def is_direct_globally_disabled():
    try:
        return not bool(current_app.config.get('DIRECT_ENABLED', True))
    except Exception:
        return False


def users_follow_each_other(user_a, user_b):
    if not user_a or not user_b:
        return False
    return bool(user_a.is_following(user_b) and user_b.is_following(user_a))


def get_membership(conversation_id, user_id):
    return ConversationMember.query.filter_by(conversation_id=conversation_id, user_id=user_id).first()


def can_user_access_group_conversation(conversation, user):
    if not conversation or not conversation.is_group:
        return True
    if not user:
        return False

    slug = (conversation.slug or '').strip().lower()
    static_members = GROUP_CHAT_PARTICIPANTS.get(slug)
    if static_members is None:
        return True

    return (user.username or '').strip().lower() in set(static_members)


def conversation_room_name(conversation_id):
    return f'conversation:{conversation_id}'


def serialize_group_member(member):
    user = member.user
    return {
        'username': user.username if user else '',
        'profile_pic': user.profile_pic if user else None,
        'is_admin': bool(member.is_admin),
    }


def get_group_members(conversation_id):
    return ConversationMember.query.join(User).filter(
        ConversationMember.conversation_id == conversation_id
    ).order_by(
        ConversationMember.is_admin.desc(),
        ConversationMember.joined_at.asc(),
        User.username.asc(),
    ).all()


def build_members_payload(conversation_id):
    members = get_group_members(conversation_id)
    return [serialize_group_member(member) for member in members]


def emit_group_members_updated(conversation_id):
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return
    socketio.emit(
        'direct:members-updated',
        {'conversation_id': conversation_id, 'members': build_members_payload(conversation_id)},
        room=conversation_room_name(conversation_id),
    )


def emit_group_updated(conversation):
    if not conversation:
        return
    socketio.emit(
        'direct:group-updated',
        {'conversation_id': conversation.id, 'title': conversation.title, 'group_photo': conversation.group_photo},
        room=conversation_room_name(conversation.id),
    )


def emit_presence_for_user(user, is_online):
    if not user:
        return
    memberships = ConversationMember.query.filter_by(user_id=user.id).all()
    payload = {'user_id': user.id, 'username': user.username, 'is_online': bool(is_online)}
    for membership in memberships:
        socketio.emit('direct:presence', payload, room=conversation_room_name(membership.conversation_id))


def ensure_group_conversation(slug):
    clean_slug = (slug or '').strip().lower()
    if not clean_slug:
        return None

    conversation = Conversation.query.filter_by(slug=clean_slug, is_group=True).first()
    if clean_slug not in GROUP_CHAT_PARTICIPANTS:
        return conversation

    changed = False
    if not conversation:
        conversation = Conversation(slug=clean_slug, title=clean_slug, is_group=True)
        db.session.add(conversation)
        db.session.flush()
        changed = True

    static_members = GROUP_CHAT_PARTICIPANTS.get(clean_slug) or []
    static_admins = set(GROUP_CHAT_ADMINS.get(clean_slug) or [])

    allowed_users = User.query.filter(User.username.in_(static_members)).all()
    allowed_by_username = {user.username: user for user in allowed_users}
    allowed_user_ids = {user.id for user in allowed_users}

    for username in static_members:
        user = allowed_by_username.get(username)
        if not user:
            continue
        membership = get_membership(conversation.id, user.id)
        should_be_admin = username in static_admins
        if not membership:
            db.session.add(ConversationMember(conversation_id=conversation.id, user_id=user.id, is_admin=should_be_admin))
            changed = True
            continue
        if membership.is_admin != should_be_admin:
            membership.is_admin = should_be_admin
            changed = True

    existing_members = ConversationMember.query.filter_by(conversation_id=conversation.id).all()
    for member in existing_members:
        if member.user_id in allowed_user_ids:
            continue
        db.session.delete(member)
        changed = True

    if changed:
        db.session.commit()
        emit_group_members_updated(conversation.id)

    return conversation


def get_or_create_dm_conversation(current_user_id, target_user_id):
    current_memberships = ConversationMember.query.filter_by(user_id=current_user_id).all()
    candidate_ids = [membership.conversation_id for membership in current_memberships]

    if candidate_ids:
        candidates = Conversation.query.filter(Conversation.id.in_(candidate_ids), Conversation.is_group.is_(False)).all()
        for conversation in candidates:
            members = ConversationMember.query.filter_by(conversation_id=conversation.id).all()
            member_ids = {member.user_id for member in members}
            if member_ids == {current_user_id, target_user_id}:
                return conversation

    conversation = Conversation(is_group=False)
    db.session.add(conversation)
    db.session.flush()
    db.session.add(ConversationMember(conversation_id=conversation.id, user_id=current_user_id, is_admin=False))
    db.session.add(ConversationMember(conversation_id=conversation.id, user_id=target_user_id, is_admin=False))
    db.session.commit()
    return conversation


def serialize_direct_message(message, current_user_id):
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username if message.sender else '',
        'sender_profile_pic': message.sender.profile_pic if message.sender else None,
        'content': message.content,
        'media_url': message.media_url,
        'created_at': message.created_at.isoformat() if message.created_at else None,
        'is_mine': message.sender_id == current_user_id,
    }


def serialize_direct_message_broadcast(message):
    return {
        'id': message.id,
        'conversation_id': message.conversation_id,
        'sender_id': message.sender_id,
        'sender_username': message.sender.username if message.sender else '',
        'sender_profile_pic': message.sender.profile_pic if message.sender else None,
        'content': message.content,
        'media_url': message.media_url,
        'created_at': message.created_at.isoformat() if message.created_at else None,
    }


def get_conversation_pinned_message(conversation_id, current_user_id):
    conversation = Conversation.query.get(conversation_id)
    if not conversation or not conversation.pinned_message_id:
        return None

    message = DirectChatMessage.query.filter_by(id=conversation.pinned_message_id, conversation_id=conversation_id).first()
    if not message:
        return None

    return serialize_direct_message(message, current_user_id)


def can_manage_group(conversation_id, user_id):
    membership = get_membership(conversation_id, user_id)
    return bool(membership and membership.is_admin)


def get_latest_message_id(conversation_id):
    last_message = DirectChatMessage.query.filter_by(conversation_id=conversation_id).order_by(DirectChatMessage.id.desc()).first()
    return last_message.id if last_message else None


def mark_conversation_read(conversation_id, user_id):
    membership = get_membership(conversation_id, user_id)
    if not membership:
        return

    latest_message_id = get_latest_message_id(conversation_id)
    if latest_message_id is None:
        return

    if membership.last_read_message_id != latest_message_id:
        membership.last_read_message_id = latest_message_id
        db.session.commit()

    try:
        latest_message_id = get_latest_message_id(conversation_id)
        if latest_message_id is None:
            return

        members = ConversationMember.query.filter_by(conversation_id=conversation_id).all()
        if not members:
            return

        all_seen = True
        for m in members:
            if not m.last_read_message_id or m.last_read_message_id < latest_message_id:
                all_seen = False
                break

        if all_seen:
            message = DirectChatMessage.query.get(latest_message_id)
            if message and not message.all_read:
                message.all_read = True
                db.session.commit()
                socketio.emit(
                    'direct:message-all-read',
                    {'conversation_id': conversation_id, 'message_id': latest_message_id},
                    room=conversation_room_name(conversation_id),
                )
    except Exception:
        pass


def get_unread_message_count(conversation_id, user_id, last_read_message_id):
    query = DirectChatMessage.query.filter(
        DirectChatMessage.conversation_id == conversation_id,
        DirectChatMessage.sender_id != user_id,
    )
    if last_read_message_id:
        query = query.filter(DirectChatMessage.id > last_read_message_id)
    return query.count()


def get_direct_unread_total(user_id):
    if not user_id:
        return 0

    memberships = ConversationMember.query.filter_by(user_id=user_id).all()
    total = 0
    for membership in memberships:
        conversation = membership.conversation
        if not conversation:
            continue
        total += get_unread_message_count(
            conversation_id=conversation.id,
            user_id=user_id,
            last_read_message_id=membership.last_read_message_id,
        )
    return total


def build_direct_inbox_items(current_user_id, current_filter='all', search_query='', for_api=False):
    current_user = User.query.get(current_user_id)
    if not current_user:
        return []

    memberships = ConversationMember.query.filter_by(user_id=current_user_id).all()
    conversations = []

    for membership in memberships:
        conversation = membership.conversation
        if not conversation:
            continue
        if conversation.is_group:
            synchronized = ensure_group_conversation(conversation.slug)
            if not synchronized:
                continue
            conversation = synchronized
            if not get_membership(conversation.id, current_user_id):
                continue
        if not can_user_access_group_conversation(conversation, current_user):
            continue

        members = get_group_members(conversation.id)
        last_message = DirectChatMessage.query.filter_by(conversation_id=conversation.id).order_by(DirectChatMessage.id.desc()).first()

        time_value = last_message.created_at if last_message and last_message.created_at else conversation.created_at
        item = {
            'id': conversation.id,
            'conversation_id': conversation.id,
            'slug': conversation.slug,
            'direct_key': conversation.slug,
            'is_group': bool(conversation.is_group),
            'title': '',
            'subtitle': '',
            'preview': 'Sem mensagens ainda.',
            'avatar_pic': None,
            'avatar_text': 'D',
            'time': time_value,
            'last_message': serialize_direct_message(last_message, current_user_id) if last_message else None,
            'members_count': len(members),
        }

        unread_count = get_unread_message_count(conversation.id, current_user_id, membership.last_read_message_id)
        item['unread_count'] = unread_count
        item['is_unread'] = unread_count > 0

        if conversation.is_group:
            title = (conversation.title or conversation.slug or 'grupo').strip()
            item['title'] = title
            item['subtitle'] = f'{len(members)} participantes'
            item['preview'] = last_message.content if last_message and last_message.content else 'Grupo criado.'
            item['avatar_pic'] = conversation.group_photo
            item['avatar_text'] = title[0].upper() if title else 'G'
        else:
            other_member = next((member for member in members if member.user_id != current_user_id and member.user), None)
            if not other_member:
                continue
            item['direct_key'] = other_member.user.username
            item['title'] = '@' + other_member.user.username
            item['subtitle'] = other_member.user.name or ''
            item['avatar_pic'] = other_member.user.profile_pic
            item['avatar_text'] = other_member.user.username[0].upper() if other_member.user.username else 'U'
            if last_message and last_message.content:
                prefix = 'Voce: ' if last_message.sender_id == current_user_id else ''
                item['preview'] = prefix + last_message.content

        if not item['direct_key']:
            continue

        if search_query:
            searchable = (item['title'] + ' ' + item['subtitle'] + ' ' + item['preview']).lower()
            if search_query not in searchable:
                continue

        if current_filter == 'unread' and not item['is_unread']:
            continue

        conversations.append(item)

    conversations.sort(key=lambda convo: convo['time'] or datetime.min, reverse=True)

    if for_api:
        for item in conversations:
            item['time'] = item['time'].isoformat() if item.get('time') else None

    return conversations


def get_message_reaction_summary(message_id):
    rows = db.session.query(MessageReaction.reaction, func.count(MessageReaction.id)).filter(MessageReaction.message_id == message_id).group_by(MessageReaction.reaction).all()
    reactions = {r[0]: r[1] for r in rows}
    reactors = {}
    for reaction in reactions.keys():
        users = db.session.query(User.username).join(MessageReaction, User.id == MessageReaction.user_id).filter(MessageReaction.message_id == message_id, MessageReaction.reaction == reaction).all()
        reactors[reaction] = [u[0] for u in users]
    return {'reactions': reactions, 'reactors': reactors}

