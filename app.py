import logging
import os
import sys

from flask import Flask

from config import Config
from extensions import socketio
from models import (
    Comment,
    Conversation,
    ConversationMember,
    DirectChatMessage,
    Event,
    Message,
    MessageReaction,
    MuralPost,
    Notification,
    Post,
    User,
    br_time,
    db,
    followers,
    post_likes,
)
from services.startup_service import initialize_database
from services.template_service import register_error_handlers, register_template_utils


def _configure_logger(app: Flask) -> None:
    log_path = app.config.get('SPOTTED_ERROR_LOG', 'instance/error.log')
    if os.path.dirname(log_path):
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
    app.logger.addHandler(file_handler)

    logging.getLogger('engineio').setLevel(logging.ERROR)
    logging.getLogger('socketio').setLevel(logging.ERROR)


def _register_blueprints(app: Flask) -> None:
    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.direct import direct_bp
    from routes.feed import feed_bp
    from routes.mural import mural_bp
    from routes.notifications import notifications_bp
    from routes.perfil import perfil_bp
    from routes.public import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(feed_bp)
    app.register_blueprint(perfil_bp)
    app.register_blueprint(direct_bp)
    app.register_blueprint(mural_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    # Backward-compatible endpoint aliases (legacy url_for calls without blueprint prefix)
    def add_alias(alias_name: str, target_endpoint: str, rule: str, methods=None):
        if alias_name in app.view_functions or target_endpoint not in app.view_functions:
            return
        app.add_url_rule(rule, endpoint=alias_name, view_func=app.view_functions[target_endpoint], methods=methods)

    add_alias('welcome', 'auth.welcome', '/')
    add_alias('login', 'auth.login', '/login', methods=['POST'])
    add_alias('registro', 'auth.registro', '/registro', methods=['POST'])
    add_alias('logout', 'auth.logout', '/logout')

    add_alias('notificacoes', 'notifications.notificacoes', '/notificacoes')
    add_alias('api_mark_notification_read', 'notifications.api_mark_notification_read', '/api/notifications/<int:notif_id>/read', methods=['POST'])
    add_alias('denunciar', 'notifications.denunciar', '/denunciar', methods=['POST'])

    add_alias('public_index', 'public.public_index', '/public/')
    add_alias('public_files', 'public.public_files', '/public/<path:filename>')

    add_alias('direct', 'direct.direct', '/direct')
    add_alias('direct_conversation', 'direct.direct_conversation', '/direct/conversa/<username>')

    add_alias('perfil', 'perfil.perfil', '/perfil/<username>')
    add_alias('perfil_por_remetente', 'perfil.perfil_por_remetente', '/perfil_por_remetente')
    add_alias('editar_perfil', 'perfil.editar_perfil', '/editar_perfil', methods=['POST'])
    add_alias('seguir', 'perfil.seguir', '/seguir/<username>')
    add_alias('enviar_recado', 'perfil.enviar_recado', '/enviar_recado/<int:user_id>', methods=['POST'])
    add_alias('toggle_verificacao', 'admin.toggle_verificacao', '/toggle_verificacao/<username>', methods=['POST'])


def create_app() -> Flask:
    app = Flask(__name__)
    sys.modules.setdefault('app', sys.modules[__name__])

    app.config.from_object(Config)
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY ausente. Defina SECRET_KEY no arquivo .env antes de iniciar a aplicacao.')
    app.permanent_session_lifetime = Config.PERMANENT_SESSION_LIFETIME

    if not os.path.isabs(app.config['PUBLIC_FOLDER']):
        app.config['PUBLIC_FOLDER'] = os.path.join(app.root_path, app.config['PUBLIC_FOLDER'])
    if not os.path.isabs(app.config['UPLOAD_FOLDER']):
        app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])

    _configure_logger(app)

    db.init_app(app)
    socketio.init_app(
        app,
        cors_allowed_origins=app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '*'),
        async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
        engineio_logger=False,
        logger=False,
        allow_upgrades=app.config.get('SOCKETIO_ALLOW_UPGRADES', True),
        async_handlers=True,
        max_http_buffer_size=20 * 1024 * 1024,
    )

    register_template_utils(app)
    register_error_handlers(app)
    _register_blueprints(app)

    with app.app_context():
        initialize_database()

    return app


app = create_app()


if __name__ == '__main__':
    auto_reload = os.getenv('APP_AUTO_RELOAD', 'true').strip().lower() in ('1', 'true', 'yes')
    debug_mode = os.getenv('FLASK_DEBUG', 'true' if auto_reload else 'false').strip().lower() in ('1', 'true', 'yes')
    socketio.run(app, host='127.0.0.1', port=5000, debug=debug_mode, use_reloader=auto_reload)
