#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Quick test script to validate that routes are correctly registered.
"""

from app import app

print("=" * 60)
print("Testing Route Registration")
print("=" * 60)

# List all registered routes
with app.app_context():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'rule': str(rule),
            'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'})
        })

    # Sort by endpoint for clarity
    routes.sort(key=lambda x: x['endpoint'])

    print("\nRegistered Routes:")
    print("-" * 60)

    for route in routes:
        if not route['endpoint'].startswith('static'):
            print(f"  {route['endpoint']:30} {route['rule']:35} {route['methods']}")

    print("\n" + "=" * 60)
    print("Checking for 'feed.feed' endpoint...")
    print("=" * 60)

    endpoints = [r['endpoint'] for r in routes]
    if 'feed.feed' in endpoints:
        print("✓ feed.feed endpoint found!")
    else:
        print("✗ feed.feed endpoint NOT found!")
        print("Available feed endpoints:")
        for ep in [e for e in endpoints if 'feed' in e]:
            print(f"  - {ep}")

print("\nTest complete!")

