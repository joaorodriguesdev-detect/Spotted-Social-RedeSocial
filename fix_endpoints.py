#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

files_to_fix = {
    'routes/feed.py': [
        ("url_for('eventos')", "url_for('feed.eventos')"),
        ("url_for('search')", "url_for('feed.search')"),
        ("url_for('welcome')", "url_for('welcome')"),
    ],
    'routes/perfil.py': [],
    'routes/direct.py': [],
}

for filepath, replacements in files_to_fix.items():
    if not replacements:
        continue

    full_path = filepath
    print(f"Processing {full_path}...")

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    for old, new in replacements:
        content = content.replace(old, new)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Fixed {full_path}")

print("\n✅ All done!")

