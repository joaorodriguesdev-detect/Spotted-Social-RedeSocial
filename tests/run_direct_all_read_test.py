#!/usr/bin/env python3
"""
Simple end-to-end test script for the "all read" flow in Direct Chat.

This script uses Flask's test_client and Flask-SocketIO's test_client to
simulate two users (sender and receiver). It will:
 - create two users and a DM conversation between them
 - connect two socket clients (they join their personal rooms on connect)
 - both join the conversation room
 - sender posts a message via the HTTP API
 - receiver posts a read mark via the HTTP API
 - assert that the sender receives a 'direct:message-all-read' socket event

Run from the repository root with:

    python -u tests/run_direct_all_read_test.py

"""
import sys
import os
import uuid
import time

# Ensure repository root is on sys.path so `import app` works when running from tests/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app, db, User, get_or_create_dm_conversation, socketio


def make_user(unique_suffix, name_prefix="Test"):
    username = f"test_{unique_suffix}"
    existing = User.query.filter_by(username=username).first()
    if existing:
        return existing
    u = User(name=f"{name_prefix} {unique_suffix}", username=username, password='x')
    db.session.add(u)
    db.session.commit()
    return u


def main():
    with app.app_context():
        # Ensure a clean pair of test users
        sfx1 = uuid.uuid4().hex[:6]
        sfx2 = uuid.uuid4().hex[:6]
        sender = make_user(sfx1, name_prefix='Sender')
        receiver = make_user(sfx2, name_prefix='Receiver')

        # Create or get a DM conversation
        conversation = get_or_create_dm_conversation(sender.id, receiver.id)

        # Create flask test clients and set session user_id for each
        flask_a = app.test_client()
        flask_b = app.test_client()
        with flask_a.session_transaction() as sess:
            sess['user_id'] = sender.id
            sess['username'] = sender.username
            sess['name'] = sender.name
            sess['is_admin'] = False
        with flask_b.session_transaction() as sess:
            sess['user_id'] = receiver.id
            sess['username'] = receiver.username
            sess['name'] = receiver.name
            sess['is_admin'] = False

        # Create socketio test clients bound to their flask clients
        sock_a = socketio.test_client(app, flask_test_client=flask_a)
        sock_b = socketio.test_client(app, flask_test_client=flask_b)

        # Both join the conversation room
        sock_a.emit('direct:join', {'conversation_id': conversation.id})
        sock_b.emit('direct:join', {'conversation_id': conversation.id})

        # Drain any received events (presence, notifications, joined acks)
        _ = sock_a.get_received()
        _ = sock_b.get_received()

        # Sender posts a message via HTTP API
        resp = flask_a.post(f'/api/direct/conversations/{conversation.id}/messages', json={'content': 'Olá, teste!'})
        if resp.status_code not in (200, 201):
            print('FAILED: sending message returned', resp.status_code, resp.data)
            sys.exit(1)

        # Give the server a moment to process and emit events
        time.sleep(0.2)

        # Receiver marks conversation as read
        resp2 = flask_b.post(f'/api/direct/conversations/{conversation.id}/read')
        if resp2.status_code != 200:
            print('FAILED: marking read returned', resp2.status_code, resp2.data)
            sys.exit(1)

        # Wait a short moment for the socket emit to reach clients
        time.sleep(0.2)

        # Check events received by sender socket for 'direct:message-all-read'
        rec = sock_a.get_received()
        found = None
        for ev in rec:
            if ev.get('name') == 'direct:message-all-read':
                found = ev.get('args')[0] if ev.get('args') else ev.get('args')
                break

        if not found:
            print('FAILED: did not receive direct:message-all-read on sender socket. Events:', rec)
            sys.exit(1)

        print('OK: received direct:message-all-read ->', found)
        sys.exit(0)


if __name__ == '__main__':
    main()


