#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Integration test to verify posting and commenting functionality.
"""

import sys
import json
from app import app, db, User, Post, Comment

def setup_test_data():
    """Create test user and post"""
    with app.app_context():
        # Check if test user exists
        user = User.query.filter_by(username='testuser').first()
        if not user:
            user = User(username='testuser', password='test123', name='Test User')
            db.session.add(user)
            db.session.commit()
            print("OK: Created test user: testuser")

        # Create a test post
        post = Post(content='Test post for commenting', user_id=user.id)
        db.session.add(post)
        db.session.commit()
        print(f"OK: Created test post with ID: {post.id}")

        return user.id, post.id

def test_feed_endpoint():
    """Test if feed endpoint returns correctly"""
    with app.test_client() as client:
        print("\n" + "=" * 60)
        print("Testing /feed endpoint")
        print("=" * 60)

        # Try to access feed without authentication
        response = client.get('/feed')
        print(f"  GET /feed (no auth): {response.status_code}")

        # Login first
        user = User.query.filter_by(username='testuser').first()
        with client:
            client.post('/login', data={'username': 'testuser', 'password': 'test123'})

            # Now try feed with authentication
            response = client.get('/feed')
            print(f"  GET /feed (with auth): {response.status_code}")

            if response.status_code == 200:
                print("  OK: Feed endpoint working!")
            else:
                print(f"  FAIL: Feed endpoint failed: {response.data}")

def test_comment_endpoint(user_id, post_id):
    """Test if commenting endpoint works"""
    with app.test_client() as client:
        print("\n" + "=" * 60)
        print("Testing /comentar endpoint")
        print("=" * 60)

        with client:
            # Login
            response = client.post('/login', data={'username': 'testuser', 'password': 'test123'})
            print(f"  Login: {response.status_code}")

            # Post a comment
            response = client.post(f'/comentar/{post_id}', data={
                'comment_content': 'This is a test comment'
            }, headers={'X-Requested-With': 'XMLHttpRequest'})
            print(f"  POST /comentar/{post_id} (AJAX): {response.status_code}")

            if response.status_code in [200, 201]:
                try:
                    data = json.loads(response.data)
                    if data.get('ok'):
                        print(f"  OK: Comment posted successfully! Comment ID: {data.get('comment_id')}")
                    else:
                        print(f"  FAIL: Comment failed: {data}")
                except:
                    print(f"  Response: {response.data}")
            else:
                print(f"  FAIL: Comment endpoint failed: {response.status_code}")
                print(f"  Response: {response.data}")

def test_post_endpoint():
    """Test if posting endpoint works"""
    with app.test_client() as client:
        print("\n" + "=" * 60)
        print("Testing /postar endpoint")
        print("=" * 60)

        with client:
            # Login
            response = client.post('/login', data={'username': 'testuser', 'password': 'test123'})
            print(f"  Login: {response.status_code}")

            # Post content
            response = client.post('/postar', data={
                'content': 'This is a test post',
                'anon_mode': 'false'
            }, follow_redirects=False)
            print(f"  POST /postar: {response.status_code}")

            if response.status_code in [200, 302]:  # Either rendered or redirected
                print(f"  OK: Post endpoint working!")
            else:
                print(f"  FAIL: Post endpoint failed: {response.status_code}")
                print(f"  Response: {response.data}")

if __name__ == '__main__':
    print("Starting integration tests...")

    try:
        with app.app_context():
            user_id, post_id = setup_test_data()

            test_feed_endpoint()
            test_post_endpoint()
            test_comment_endpoint(user_id, post_id)

            print("\n" + "=" * 60)
            print("Integration tests completed!")
            print("=" * 60)
    except Exception as e:
        print(f"\nERROR during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

