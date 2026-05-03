# AGENTS Guide - spotted-social

## Snapshot
  - Monolith Flask app scaffold: `app.py` now primarily wires the Flask application, registers blueprints and SocketIO, and delegates models and domain helpers to dedicated packages. HTTP route handlers are organized as blueprints under `routes/` (see `routes/feed.py`, `routes/perfil.py`, `routes/direct.py`, `routes/mural.py`, `routes/admin.py`, `routes/auth.py`, `routes/notifications.py`, `routes/public.py`). Many formerly in-file helpers and DB startup logic have been moved into the `services/` package and `models/` package (see notes below). `app.py` still contains some legacy routes and real-time SocketIO handlers but is no longer the single file holding all models/helpers.
- Server-rendered Jinja views live in `templates/`.
- User uploads are in `static/uploads/`; app-level public assets are in `static/public/` and served by the app.
- Public assets are enumerated by `/public/` and served at `/public/<path:filename>`.
- DB is Flask-SQLAlchemy with SQLite by default (`sqlite:///spotted.db`), overridable via `DATABASE_URL`.

## Core Architecture and Data Flow
 - Models are defined in the `models/` package (`models/__init__.py`) and include: `User`, `Post`, `Comment`, `Notification`, `Message`, `Event`, `MuralPost`, plus messaging models `Conversation`, `ConversationMember`, `DirectChatMessage`, and `MessageReaction`. `models.__init__` also exposes `db`, `post_likes`, `followers` and helper `br_time()` used throughout the app.
- Import-time startup is handled by `services.startup_service.initialize_database()` which runs `db.create_all()` and a set of `ensure_*` schema fixers (ALTER TABLE helpers), backfills nulls, and seeds an `admin` user when missing. `app.py` calls `initialize_database()` inside the application context during app creation.
- Feed:
  - `/feed` renders initial chunk (`get_feed_chunk`).
  - `/feed/more` returns HTML partial (`_feed_posts.html`) for infinite scroll.
- Search:
  - `/search` renders server-side page state for users/events categories.
  - `/api/search` returns JSON for live search/autocomplete.
- Events:
  - `/criar_evento` creates an `Event` and mirrors it into the feed as a `Post` using `build_event_post_content(...)` which uses the marker `"📢 NOVO EVENTO:"`.
  - `/editar_evento` updates `Event` and attempts to `sync_event_feed_post(...)` to keep the mirrored feed post consistent.

- Server-side static group configuration: `app.py` defines `GROUP_CHAT_PARTICIPANTS` and `GROUP_CHAT_ADMINS` dicts. When a conversation slug matches those entries, `ensure_group_conversation(...)` will create/sync the conversation and its members/admins at import/runtime. This enforces server-controlled membership for specific group slugs.

Note: blueprint registration is performed near the end of `app.py` (the file imports `routes.feed`, `routes.perfil`, `routes.direct` and registers their blueprints). When adding or moving routes, update the `routes/` package and the registration in `app.py` accordingly.

### Key helper functions (quick pointers)

- `get_feed_chunk(cursor_ts=None, cursor_id=None, limit=FEED_PAGE_SIZE)` — now defined in `services/feed_service.py`. Used by `/feed` and `/feed/more` to fetch a page of posts. Returns `(posts, has_more, next_cursor_ts, next_cursor_id)`. Example: `posts, has_more, next_cursor_ts, next_cursor_id = get_feed_chunk()` (importable via `from services import get_feed_chunk`).
- `annotate_posts_with_like_info(posts, user_id)` — in `services/feed_service.py`. Adds `liked_by_me` boolean to Post objects to avoid per-post queries before rendering partials/templates.
- `build_event_post_content(title, location, event_date, description, username)` and `sync_event_feed_post(...)` — in `services/feed_service.py`. Produces and syncs the mirrored feed post body for events (marker: `📢 NOVO EVENTO:`).
- Conversation / Direct helpers — moved to `services/direct_service.py`: `ensure_group_conversation(slug)`, `get_or_create_dm_conversation(current_user_id, target_user_id)`, `mark_conversation_read(conversation_id, user_id)`, `build_direct_inbox_items(...)`, `get_unread_message_count(...)`, `get_direct_unread_total(...)`, and related membership/serialization helpers.
- Direct availability helpers (`is_direct_blocked_for_system_admin()`, `is_direct_temporarily_disabled_for_users()`, `is_direct_globally_disabled()`) now live in `services/direct_service.py` and consult `current_app.config['DIRECT_ENABLED']` where appropriate.
- `br_time()` — small helper moved to `models/__init__.py` as `br_time()` and is used as the default factory for model timestamps.

## Real-time / Direct Chat
- Uses `Flask-SocketIO` for presence, typing, and message broadcast events. Socket handlers live in `app.py` and use session auth.
- Conversations can be 1:1 (DM) or group (is_group flag). Group membership and admin flags are stored in `ConversationMember`.

## Frontend Organization (Current)
- `templates/index.html` loads page-specific assets from `public/css/index-search.css` and `public/js/index-search.js`.
- `templates/eventos.html` loads `public/css/eventos.css` and `public/js/eventos.js`.
- Keep JS in `static/public/js/` and CSS in `static/public/css/`.
- Avoid putting large inline JS/CSS back into templates unless strictly needed.

## Configuration & Environment
- Important environment variables:
  - `DATABASE_URL` — override DB connection (default `sqlite:///spotted.db`).
  - `SECRET_KEY` — session and security secret (default hardcoded fallback present in `app.py`).
  - `FEED_PAGE_SIZE` — controls page size; allowed values are `6`, `8`, `12` (other values fallback to `8`).

  - `DIRECT_MAINTENANCE` — (retired) previously used to temporarily block non-admin users from Direct during maintenance; this environment variable is no longer consumed by the application. The temporary maintenance-before-request hook was removed and related helpers now return False for compatibility.
  - Uploads / limits: configuration lives in `config.py` (see `Config.UPLOAD_FOLDER` and `Config.MAX_CONTENT_LENGTH`). By default uploads are stored under `static/uploads` and MAX_CONTENT_LENGTH has been increased from earlier notes (the repo default is 30MB via `Config`). Be aware uploads are saved directly and there is no extension/content-type whitelist in the current code (see `services/image_service.py` for image helper utilities used by upload flows).

    - `DIRECT_ENABLED` — controlled via `config.py` (`Config.DIRECT_ENABLED`, environ var `DIRECT_ENABLED`) and consulted by `services/direct_service.is_direct_globally_disabled()`. Disabling Direct globally is done via configuration rather than editing `app.py`.

## Project Conventions That Matter
- Session contract used across templates/routes: `user_id`, `username`, `name`, `is_admin`, `profile_pic`.
- Username normalization is lowercase in login/register flows.
- Event mirror posts are identified by marker text "📢 NOVO EVENTO:"; producer/parser must stay aligned.
- Relative time and defaults use local helper `br_time()` (UTC-3 offset logic).

## Security & Safety Notes (observations)
These are items found during review that need attention before production use:

- Hardcoded admin seed: `app.py` will create an `admin` user with a hardcoded password (`Migo@2026!#`) when missing. Recommend using an environment-provided admin password or disabling automatic seeding for production.

- No formal DB migrations: the project relies on `db.create_all()` and a few manual `ALTER TABLE` calls (`ensure_*` helpers). This is fragile — add Alembic (or Flask-Migrate) for repeatable migrations.

- File upload restrictions: uploads are saved under `static/uploads/` using UUID filenames, but there's no explicit allowed-extension check. Consider whitelisting extensions and validating image content (PIL file header check) to avoid arbitrary file uploads.

- CSRF protection: there is no CSRF protection for form POST endpoints. If deploying publicly, add CSRF tokens (Flask-WTF or similar) to prevent cross-site request forgery.

- Session cookie hardening: `app.config` does not set `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, or `SESSION_COOKIE_SAMESITE`. Configure these for production.

- SocketIO CORS: `SocketIO(..., cors_allowed_origins='*')` is permissive; prefer restricting origins in production.

- Rate limiting & brute-force protections: login and APIs do not implement rate limiting. Add a rate limiter (Flask-Limiter) to protect sensitive endpoints.

 - Ad-hoc scripts present in `scripts/`: `scripts/check_feed.py` (simple smoke test using Flask's `test_client` that fetches `/feed`) and `scripts/convert_uploads_to_webp.py` (converts image files under `static/uploads` to WebP and can optionally update DB image links). There are no `migrar.py` / `corrigir_vazios.py` files in this repository snapshot; if you rely on ad-hoc DDL/fix scripts, search the repo or implement migration steps carefully. Prefer using proper migration tooling (Alembic / Flask-Migrate) instead.

- A basic end-to-end test exists at `tests/run_direct_all_read_test.py` which exercises the Direct "all read" flow using Flask's `test_client` and Flask-SocketIO's `test_client`. Run it from the repository root with:

  ```powershell
  python -u tests/run_direct_all_read_test.py
  ```

  Note: the script talks to the local SQLite DB (`instance/spotted.db`) and will create test users/conversations — back up or use a disposable DB when running.

## UX / Content Suggestions (minor)
 - Mutual-follow restriction: the API returns a Portuguese error when adding a group member if users are not following each other. This message has already been updated in the current code. Current server response (in `app.py`, POST `/api/direct/conversations/<int:conversation_id>/members`) is:

  "Para adicionar alguém ao grupo, é necessário que ambos se sigam mutuamente."

  Frontend suggestion: the app can show a dedicated element in the add-member modal with id `group-add-error` and set its text when the API returns the mutual-follow error (e.g. `function showMutualFollowError(msg) { /* set #group-add-error text */ }`).

## Developer Workflows
- Run locally (dev):
  ```powershell
  python app.py
  ```
- Quick syntax check:
  ```powershell
  python -m py_compile app.py
  ```

- Run the provided end-to-end Direct test (works against `instance/spotted.db`):

  ```powershell
  python -u tests/run_direct_all_read_test.py
  ```

 - Migration helpers (ad-hoc): database initialization and ALTER helpers are implemented in `services/startup_service.py` (called by `app.create_app()` via `initialize_database()`). There are no `migrar.py` / `corrigir_vazios.py` files in this workspace snapshot; inspect `services/startup_service.py` if you need to understand runtime ALTER TABLE helpers and which columns are backfilled. Prefer running any destructive scripts against a copy of the DB.

## Recommended Immediate Improvements (actionable checklist)
1. Replace hardcoded admin seeding with environment-driven value or document the default admin behavior clearly and rotate the password before production.
2. Add DB migrations (Alembic / Flask-Migrate) and remove/replace runtime `ALTER TABLE` patterns.
3. Add allowed file extensions and validate uploads (images) server-side.
4. Add CSRF protection to POST endpoints and forms.
5. Harden session cookie settings in config.
6. Restrict SocketIO CORS to known origins in production.
7. Add rate limiting on login and APIs.
8. Add unit/integration tests and CI workflow.

## Change Safety Notes
- Be careful editing initialization in `app.py`; side effects run at import time (DB creation, schema helpers, admin seed).
- When changing event text format, update both event writer and any event parsing/render logic (feed mirror uses marker `📢 NOVO EVENTO:`).
- Keep route/template pairs in sync; this codebase is tightly coupled by context variables.
- If moving/renaming public assets, update `url_for('public_files', filename=...)` references in templates.

- Change safety: the ad-hoc scripts in `scripts/` (for example `convert_uploads_to_webp.py`) and the tests in `tests/` will modify the SQLite DB (`instance/spotted.db`). Always work on a copy or disposable DB and inspect any script before running.

If you want, I can open a PR with a small set of changes: (a) update the mutual-follow error message in `app.py`, (b) add a minimal ALLOWED_EXTENSIONS check for uploads, and (c) add documentation to `README.md` describing env vars and the seeded admin note. Tell me which items you'd like implemented and I'll apply them.

## README and repository documentation

I added recommendations for a small README for developer onboarding. A `README.md` should include:

- Project description and quick start (how to run locally with `python app.py`).
- Important environment variables (`DATABASE_URL`, `SECRET_KEY`, `FEED_PAGE_SIZE`) and recommended defaults.
- Note about the seeded admin user: at import-time the app may create an `admin` account with a hardcoded password (present in `app.py`). This is convenient for local testing but MUST be changed or disabled in any production deployment. Rotate the password and/or read it from `ADMIN_PASSWORD` environment variable.
- Security checklist: allowed file extensions for uploads, CSRF protection, session cookie hardening, SocketIO CORS restrictions, and rate limiting.

I have created a `README.md` in the repository root with a concise developer quick-start and security notes. Use it as the canonical onboarding doc and expand as you add CI/migrations/tests.
