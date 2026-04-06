# AGENTS Guide - spotted-social

## Snapshot
- Monolith Flask app: routes, models, filters, and startup setup are in `app.py`.
- Server-rendered Jinja views live in `templates/`.
- User uploads are in `static/uploads/`; app-level public assets are in `static/public/` and served by the app.
- Public assets are enumerated by `/public/` and served at `/public/<path:filename>`.
- DB is Flask-SQLAlchemy with SQLite by default (`sqlite:///spotted.db`), overridable via `DATABASE_URL`.

## Core Architecture and Data Flow
- `app.py` models: `User`, `Post`, `Comment`, `Notification`, `Message`, `Event`, plus messaging models `Conversation`, `ConversationMember`, and `DirectChatMessage` for the Direct/group chat feature.
- Import-time startup runs `db.create_all()` and additional schema helpers (`ensure_*`) which may ALTER tables at runtime; the app also backfills nulls and seeds an `admin` user when missing.
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

  - `DIRECT_MAINTENANCE` — when set (`1`, `true`, `yes`, `on`) non-admin users are prevented from accessing Direct pages and `/api/direct` endpoints; admins keep access for testing.
  - Uploads / limits: `app.py` sets `UPLOAD_FOLDER` (`static/uploads`) and `MAX_CONTENT_LENGTH` (16MB). Be aware uploads are saved directly and there is no extension/content-type whitelist in the current code.

## Project Conventions That Matter
- Session contract used across templates/routes: `user_id`, `username`, `name`, `is_admin`, `profile_pic`.
- Username normalization is lowercase in login/register flows.
- Event mirror posts are identified by marker text `"NOVO EVENTO:"`; producer/parser must stay aligned.
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

- Ad-hoc migration / fix scripts present: `migrar.py` and `corrigir_vazios.py` are included in the repo to perform SQLite DDL/cleanup. Both reference a hardcoded `DB_PATH` (`/home/SpottedSocial/...`) and should be inspected/edited before running on your machine. Prefer using a disposable DB or proper migration tooling instead.

- A basic end-to-end test exists at `tests/run_direct_all_read_test.py` which exercises the Direct "all read" flow using Flask's `test_client` and Flask-SocketIO's `test_client`. Run it from the repository root with:

  ```powershell
  python -u tests/run_direct_all_read_test.py
  ```

  Note: the script talks to the local SQLite DB (`instance/spotted.db`) and will create test users/conversations — back up or use a disposable DB when running.

## UX / Content Suggestions (minor)
- Mutual-follow restriction message: server returns a Portuguese error when adding a group member if users are not following each other. The user-facing text can be improved. Suggested replacement (more friendly):

  "Para adicionar alguém ao grupo, vocês precisam se seguir mutuamente primeiro."

  Or more conversational:

  "Só é possível adicionar ao grupo quem também te segue. Sigam-se mutuamente para liberar o convite!"

  Location to change: the error originates in `app.py` at the `/api/direct/conversations/<int:conversation_id>/members` POST handler — update the JSON error payload there.

  Frontend suggestion: the app can show a dedicated element in the add-member modal with id `group-add-error` and set its text when the API returns the mutual-follow error. Example JS snippet (already suggested by the user):

  function showMutualFollowError() { /* ... */ }

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

- Migration helpers (ad-hoc): `migrar.py` and `corrigir_vazios.py` exist to apply DDL and fix nulls for SQLite. They contain a `DB_PATH` constant that points at `/home/SpottedSocial/...` by default - edit this path before running on your environment. Prefer running these against a copy of the DB.

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
- When changing event text format, update both event writer and any event parsing/render logic (feed mirror uses marker `NOVO EVENTO:`).
- Keep route/template pairs in sync; this codebase is tightly coupled by context variables.
- If moving/renaming public assets, update `url_for('public_files', filename=...)` references in templates.

- Change safety: the ad-hoc scripts (`migrar.py`, `corrigir_vazios.py`) and the tests in `tests/` will modify the SQLite DB (`instance/spotted.db`). Always work on a copy or disposable DB and update hardcoded `DB_PATH` constants in those scripts before running.

If you want, I can open a PR with a small set of changes: (a) update the mutual-follow error message in `app.py`, (b) add a minimal ALLOWED_EXTENSIONS check for uploads, and (c) add documentation to `README.md` describing env vars and the seeded admin note. Tell me which items you'd like implemented and I'll apply them.

## README and repository documentation

I added recommendations for a small README for developer onboarding. A `README.md` should include:

- Project description and quick start (how to run locally with `python app.py`).
- Important environment variables (`DATABASE_URL`, `SECRET_KEY`, `FEED_PAGE_SIZE`) and recommended defaults.
- Note about the seeded admin user: at import-time the app may create an `admin` account with a hardcoded password (present in `app.py`). This is convenient for local testing but MUST be changed or disabled in any production deployment. Rotate the password and/or read it from `ADMIN_PASSWORD` environment variable.
- Security checklist: allowed file extensions for uploads, CSRF protection, session cookie hardening, SocketIO CORS restrictions, and rate limiting.

I have created a `README.md` in the repository root with a concise developer quick-start and security notes. Use it as the canonical onboarding doc and expand as you add CI/migrations/tests.

