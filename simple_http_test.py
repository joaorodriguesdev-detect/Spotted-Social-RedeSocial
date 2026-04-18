#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple manual test - actually test posting and commenting via HTTP requests
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def test():
    print("=" * 60)
    print("Testing Spotted Social - Posts and Comments")
    print("=" * 60)

    session = requests.Session()

    # Test 1: Check if server is running
    print("\nTest 1: Check server status")
    try:
        r = session.get(f"{BASE_URL}/")
        print(f"  GET /: {r.status_code} - OK" if r.status_code in [200, 302] else f"  FAIL: {r.status_code}")
    except Exception as e:
        print(f"  FAIL: Server not responding - {e}")
        return

    # Test 2: Login
    print("\nTest 2: Login as admin")
    r = session.post(f"{BASE_URL}/login", data={'username': 'admin', 'password': 'Migo@2026!#'})
    print(f"  Login status: {r.status_code}")

    # Test 3: Access feed
    print("\nTest 3: Access feed")
    r = session.get(f"{BASE_URL}/feed")
    print(f"  GET /feed: {r.status_code}")
    if r.status_code == 200:
        print("  OK: Feed loaded successfully")

    # Test 4: Create a post
    print("\nTest 4: Create a post")
    r = session.post(f"{BASE_URL}/postar", data={
        'content': f'Test post created at {time.time()}',
        'anon_mode': 'false'
    }, allow_redirects=False)
    print(f"  POST /postar: {r.status_code}")
    if r.status_code in [302, 200]:
        print("  OK: Post created successfully")

    # Get the latest post to comment on
    print("\nTest 5: Get latest post for commenting")
    r = session.get(f"{BASE_URL}/feed")
    # We'll assume post ID 1 exists for testing
    post_id = 1
    print(f"  Will test comment on post ID: {post_id}")

    # Test 6: Comment on post
    print("\nTest 6: Post a comment (AJAX)")
    r = session.post(
        f"{BASE_URL}/comentar/{post_id}",
        data={'comment_content': f'Test comment at {time.time()}'},
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    print(f"  POST /comentar/{post_id}: {r.status_code}")

    try:
        response_data = r.json()
        if response_data.get('ok'):
            print(f"  OK: Comment posted! ID: {response_data.get('comment_id')}")
        else:
            print(f"  FAIL: {response_data}")
    except:
        print(f"  Response: {r.text[:200]}")

    print("\n" + "=" * 60)
    print("Tests completed")
    print("=" * 60)

if __name__ == '__main__':
    test()

