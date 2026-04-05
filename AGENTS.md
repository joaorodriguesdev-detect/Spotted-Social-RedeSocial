# AGENTS Guide - spotted-social

## Snapshot
- Monolith Flask app: routes, models, filters, and startup setup are in `app.py`.
- Server-rendered Jinja views live in `templates/`.
- User uploads are in `static/uploads/`; app-level static assets are in `static/public/`.
- Public assets are served by Flask routes `/public/` and `/public/<path:filename>`.
- DB is Flask-SQLAlchemy with SQLite by default (`sqlite:///spotted.db`), overridable via `DATABASE_URL`.

## Core Architecture and Data Flow
- `app.py` models: `User`, `Post`, `Comment`, `Notification`, `Message`, `Event`.
- Import-time startup runs `db.create_all()`, ensures `user.created_at`, backfills nulls, and seeds admin if missing.
- Feed:
  - `/feed` renders initial chunk (`get_feed_chunk`).
  - `/feed/more` returns HTML partial (`_feed_posts.html`) for infinite scroll.
- Search:
  - `/search` renders page state for users/events categories.
  - `/api/search` returns JSON for live search as user types.
- Events:
  - `/criar_evento` creates `Event` and mirrors it into feed as a `Post` using `build_event_post_content(...)`.
  - `/editar_evento` updates `Event` and syncs mirrored feed post via `sync_event_feed_post(...)`.

## Frontend Organization (Current)
- `templates/index.html` loads page-specific assets from:
  - `public/css/index-search.css`
  - `public/js/index-search.js`
- `templates/eventos.html` loads page-specific assets from:
  - `public/css/eventos.css`
  - `public/js/eventos.js`
- Keep JS in `static/public/js/` and CSS in `static/public/css/`.
- Avoid putting large inline JS/CSS back into templates unless strictly needed.

## Project Conventions That Matter
- Session contract used across templates/routes: `user_id`, `username`, `name`, `is_admin`, `profile_pic`.
- Username normalization is lowercase in login/register flows.
- Event mirror posts are identified by marker text `"NOVO EVENTO:"`; producer/parser must stay aligned.
- Relative time and defaults use local helper `br_time()` (UTC-3 offset logic).
- Allowed `FEED_PAGE_SIZE` values are constrained in code (`6`, `8`, `12`).

## Event Validation Rules (Implemented)
- Backend validation in `app.py` (`parse_event_datetime`) blocks:
  - invalid date/time format
  - past date/time
- Frontend validation in `static/public/js/eventos.js` mirrors backend checks and sets `min` date on inputs.
- Preserve both layers; frontend is UX, backend is source of truth.

## Developer Workflows
- Run locally:
  ```powershell
  python app.py
  ```
- Quick syntax check:
  ```powershell
  python -m py_compile app.py
  ```

## Change Safety Notes
- Be careful editing initialization in `app.py`; side effects run at import time.
- When changing event text format, update both event writer and any event parsing/render logic.
- Keep route/template pairs in sync; this codebase is tightly coupled by context variables.
- If moving/renaming public assets, update `url_for('public_files', filename=...)` references in templates.
