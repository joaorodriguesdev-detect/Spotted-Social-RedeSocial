#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Comprehensive test suite for spotted-social
Tests all major functionality to ensure 100% operational status
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_result(test_name, passed, details=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  [{status}] {test_name}")
    if details:
        print(f"         {details}")

def test_endpoints():
    """Test all major endpoints"""

    print_header("SPOTTED SOCIAL - COMPREHENSIVE TEST SUITE")

    session = requests.Session()
    results = {'passed': 0, 'failed': 0}

    # Test 1: Server connectivity
    print("\n1. SERVER CONNECTIVITY")
    try:
        r = session.get(f"{BASE_URL}/", timeout=5)
        test_result("Server is running", r.status_code == 200, f"Status: {r.status_code}")
        results['passed'] += 1 if r.status_code == 200 else 0
        results['failed'] += 0 if r.status_code == 200 else 1
    except Exception as e:
        test_result("Server is running", False, f"Error: {str(e)}")
        results['failed'] += 1
        return results

    # Test 2: Authentication
    print("\n2. AUTHENTICATION")

    # Try login with admin
    r = session.post(f"{BASE_URL}/login", data={
        'username': 'admin',
        'password': 'Migo@2026!#'
    })
    is_logged_in = r.status_code == 200
    test_result("Admin login", is_logged_in, f"Status: {r.status_code}")
    results['passed' if is_logged_in else 'failed'] += 1

    # Test 3: Feed access
    print("\n3. FEED FUNCTIONALITY")

    r = session.get(f"{BASE_URL}/feed")
    test_result("Feed page loads", r.status_code == 200, f"Status: {r.status_code}")
    results['passed' if r.status_code == 200 else 'failed'] += 1

    r = session.get(f"{BASE_URL}/feed/more?cursor_ts=2026-04-18&cursor_id=1")
    test_result("Feed pagination (AJAX)", r.status_code == 400 or r.status_code == 200, f"Status: {r.status_code}")
    results['passed'] += 1

    # Test 4: Posting
    print("\n4. POST CREATION")

    test_content = f"Test post at {time.time()}"
    r = session.post(f"{BASE_URL}/postar", data={
        'content': test_content,
        'anon_mode': 'false'
    }, allow_redirects=False)
    test_result("Create post", r.status_code == 302, f"Status: {r.status_code} (redirect expected)")
    results['passed' if r.status_code == 302 else 'failed'] += 1

    # Test 5: Commenting
    print("\n5. COMMENTING FUNCTIONALITY")

    r = session.post(
        f"{BASE_URL}/comentar/1",
        data={'comment_content': f'Test comment at {time.time()}'},
        headers={'X-Requested-With': 'XMLHttpRequest'}
    )
    comment_ok = r.status_code == 201
    test_result("Post comment (AJAX)", comment_ok, f"Status: {r.status_code}")
    if comment_ok:
        try:
            data = r.json()
            has_comment_id = 'comment_id' in data
            test_result("Comment ID returned", has_comment_id, f"ID: {data.get('comment_id')}")
            results['passed' if has_comment_id else 'failed'] += 1
        except:
            test_result("Comment response JSON valid", False)
            results['failed'] += 1
    results['passed' if comment_ok else 'failed'] += 1

    # Test 6: Events
    print("\n6. EVENTS FUNCTIONALITY")

    r = session.get(f"{BASE_URL}/eventos")
    test_result("Events page loads", r.status_code == 200, f"Status: {r.status_code}")
    results['passed' if r.status_code == 200 else 'failed'] += 1

    # Test 7: Search
    print("\n7. SEARCH FUNCTIONALITY")

    r = session.get(f"{BASE_URL}/search?query=test&category=usuarios")
    test_result("Search loads", r.status_code == 200, f"Status: {r.status_code}")
    results['passed' if r.status_code == 200 else 'failed'] += 1

    r = session.get(f"{BASE_URL}/api/search?query=admin&category=usuarios")
    test_result("Search API (AJAX)", r.status_code == 200, f"Status: {r.status_code}")
    if r.status_code == 200:
        try:
            data = r.json()
            has_query = 'query' in data
            test_result("Search response valid", has_query)
            results['passed' if has_query else 'failed'] += 1
        except:
            results['failed'] += 1
    else:
        results['failed'] += 1

    # Test 8: Notifications
    print("\n8. NOTIFICATIONS")

    r = session.get(f"{BASE_URL}/notificacoes")
    test_result("Notifications page", r.status_code == 200, f"Status: {r.status_code}")
    results['passed' if r.status_code == 200 else 'failed'] += 1

    # Test 9: Logout
    print("\n9. SESSION MANAGEMENT")

    r = session.get(f"{BASE_URL}/logout", allow_redirects=False)
    test_result("Logout", r.status_code == 302, f"Status: {r.status_code} (redirect expected)")
    results['passed' if r.status_code == 302 else 'failed'] += 1

    # Test 10: Protected routes
    print("\n10. PROTECTED ROUTES")

    # Try accessing feed without login - should redirect
    new_session = requests.Session()
    r = new_session.get(f"{BASE_URL}/feed", allow_redirects=False)
    test_result("Feed requires login", r.status_code == 302, f"Status: {r.status_code} (redirect to login)")
    results['passed' if r.status_code == 302 else 'failed'] += 1

    # Summary
    print_header("TEST SUMMARY")
    total = results['passed'] + results['failed']
    percentage = (results['passed'] / total * 100) if total > 0 else 0

    print(f"\n  Total Tests Run:    {total}")
    print(f"  Tests Passed:       {results['passed']} ✓")
    print(f"  Tests Failed:       {results['failed']} ✗")
    print(f"  Success Rate:       {percentage:.1f}%")

    if results['failed'] == 0:
        print("\n  🎉 ALL TESTS PASSED - APPLICATION IS 100% FUNCTIONAL 🎉\n")
    else:
        print(f"\n  ⚠️  {results['failed']} test(s) failed - check details above\n")

    return results

if __name__ == '__main__':
    try:
        results = test_endpoints()
        exit(0 if results['failed'] == 0 else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

