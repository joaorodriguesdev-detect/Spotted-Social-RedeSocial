import re
from datetime import datetime, timedelta, timezone

from flask import request, session
from sqlalchemy import func

from models import Notification, User
from services.direct_service import get_direct_unread_total, is_direct_globally_disabled


def register_template_utils(app):
    @app.template_filter('joined_month_year')
    def joined_month_year_filter(ts):
        if not ts:
            return ''
        months_pt = {
            1: 'janeiro',
            2: 'fevereiro',
            3: 'marco',
            4: 'abril',
            5: 'maio',
            6: 'junho',
            7: 'julho',
            8: 'agosto',
            9: 'setembro',
            10: 'outubro',
            11: 'novembro',
            12: 'dezembro',
        }
        return f"{months_pt[ts.month]} de {ts.year}"

    @app.template_filter('post_time')
    def post_time_filter(ts):
        if not ts:
            return ''

        tz_br = timezone(timedelta(hours=-3))
        now = datetime.now(tz_br)

        try:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=tz_br)
            else:
                ts = ts.astimezone(tz_br)
        except Exception:
            try:
                now = now.replace(tzinfo=None)
                ts = ts.replace(tzinfo=None)
            except Exception:
                return ''

        delta = now - ts
        if delta.total_seconds() < 0:
            return 'agora'

        seconds = int(delta.total_seconds())
        if seconds < 60:
            return 'agora'
        minutes = seconds // 60
        if minutes < 60:
            return f'{minutes}m'
        hours = minutes // 60
        if hours < 24:
            return f'{hours}h'
        days = delta.days
        if days < 30:
            return f'{days}d'
        if delta < timedelta(days=365):
            return ts.strftime('%d/%m')
        return ts.strftime('%d/%m/%Y')

    @app.template_filter('mention')
    def mention_filter(text):
        def replace_mention(match):
            username = match.group(1).lower()
            exists = User.query.filter_by(username=username).first()
            if exists:
                return f'<a href="/perfil/{username}" class="text-indigo-500 font-bold hover:underline">@{username}</a>'
            return f'@{username}'

        return re.sub(r'@(\w+)', replace_mention, text or '')

    @app.template_global('is_verified_platform_account')
    def is_verified_platform_account(username):
        clean_username = (username or '').strip().lower()
        if not clean_username or clean_username in {'anônimo', 'anonimo'}:
            return False
        user = User.query.filter(func.lower(User.username) == clean_username).first()
        return bool(user and user.is_admin)

    @app.template_global('post_is_liked_by')
    def post_is_liked_by(post, user_id):
        try:
            if not user_id:
                return False
            return post.liked_by.filter_by(id=user_id).count() > 0
        except Exception:
            return False

    @app.context_processor
    def inject_global_unread_counters():
        direct_globally_disabled = is_direct_globally_disabled()
        user_id = session.get('user_id')
        if direct_globally_disabled or not user_id:
            return {'direct_unread_count': 0, 'direct_enabled': False}
        return {
            'direct_unread_count': get_direct_unread_total(user_id),
            'direct_enabled': True,
        }



def register_error_handlers(app):
    import traceback

    @app.errorhandler(Exception)
    def log_exception(e):
        try:
            try:
                req_info = f'{request.method} {request.path} full_url={request.url}'
            except Exception:
                req_info = 'request info unavailable'

            tb = traceback.format_exc()
            app.logger.error('Unhandled exception: %s\nRequest: %s\nTraceback:\n%s', type(e).__name__, req_info, tb)
        except Exception:
            traceback.print_exc()
        return (
            '<h1>Internal Server Error</h1><p>An unexpected error occurred. '
            'The full traceback has been written to the error log.</p>',
            500,
        )

