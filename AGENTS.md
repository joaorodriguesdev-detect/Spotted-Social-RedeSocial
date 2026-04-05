# AGENTS Guide - spotted-social

## Project Snapshot
- Single-process Flask app: backend, ORM models, and routes all live in `app.py`.
- Server-rendered UI with Jinja templates in `templates/`; uploaded media is served from `static/uploads/`.
- Persistence uses Flask-SQLAlchemy with SQLite by default (`sqlite:///spotted.db`), configurable via `DATABASE_URL`.
- No existing agent/rules docs were found via `**/{.github/copilot-instructions.md,AGENT.md,AGENTS.md,CLAUDE.md,.cursorrules,.windsurfrules,.clinerules,.cursor/rules/**,.windsurf/rules/**,.clinerules/**,README.md}`.

## Architecture and Data Flow
- `app.py` defines models (`User`, `Post`, `Comment`, `Notification`, `Message`, `Event`) plus all HTTP routes.
- Startup side effects happen at import time (`with app.app_context(): db.create_all(); ...`): schema creation + admin bootstrap.
- Feed flow: `/feed` -> query all posts desc -> render `templates/index.html`.
- Mentions flow: `mention_filter` converts `@username` to profile links in templates; `notify_mentions()` creates `Notification` rows on post/comment creation.
- Event flow: `/criar_evento` creates an `Event` and also inserts a feed `Post` containing a marker string (`"📢 NOVO EVENTO:"`), then `templates/index.html` parses that text format to render event cards.
- Profile flow: `/perfil/<username>` renders both user posts and wall messages (`Message`) in `templates/profile.html`.

## Developer Workflows (Current State)
- Run app locally:
  ```powershell
  python app.py
  ```
- Default runtime mode is debug (`app.run(debug=True)` in `app.py`).
- Environment knobs used by the app:
  - `SECRET_KEY` (falls back to hardcoded dev secret in code)
  - `DATABASE_URL` (falls back to local SQLite file)
- One-off DB maintenance scripts exist:
  - `migrar.py` (schema/column/event-table migration)
  - `corrigir_vazios.py` (fills empty `user.name`/`user.university`)
- Both scripts target a hardcoded Linux DB path (`/home/SpottedSocial/.../spotted.db`), so adjust `DB_PATH` before running locally on Windows.

## Project-Specific Conventions
- Session keys (`user_id`, `username`, `name`, `is_admin`, `profile_pic`) are treated as the auth/user context contract across routes/templates.
- Usernames are normalized to lowercase during auth/register (`login`, `registro` routes).
- Anonymous posting is explicit via form field `anon_mode=true|false` and persisted as `Post.is_anonymous`.
- Upload naming pattern:
  - Posts/events: UUID + original extension.
  - Profile pics: `pfp_<user_id>_<8char_uuid>.<ext>`.
- Localized time is implemented as UTC-3 manually (`br_time()`), then used as model defaults.

## Integration and UI Coupling Points
- Frontend relies on CDN assets (Tailwind and Font Awesome) in templates; there is no local JS/CSS build pipeline.
- Bottom nav unread badge in `templates/base.html` depends on `unread_count` passed by routes (`/feed`, `/search`, `/eventos`).
- `/api/users` supports mention autocomplete style lookups (prefix search, excludes admins).
- `templates/admin.html` references `post.reports` and `/admin/deletar/...`, but matching model fields/routes are not present in `app.py` (appears stale).

## Change Safety Notes for Agents
- Be careful with import-time DB side effects in `app.py`; changes near app initialization can alter first-run behavior.
- Keep event-post text format stable unless updating both producer (`/criar_evento`) and parser (`templates/index.html`).
- If changing like behavior, align backend toggle logic (`/like/<id>`) with optimistic UI JS in `templates/index.html` (`ajaxLike`).
- Prefer small, route-template paired edits because most behaviors are tightly coupled between Jinja markup and route return context.
