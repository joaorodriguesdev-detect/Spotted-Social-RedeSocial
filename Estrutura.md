# Refatoracao Estrutural Flask - Documento Unico

Este e o documento oficial (unico) da refatoracao de estrutura do backend Python.

## Objetivo
Reduzir o acoplamento do `app.py`, separar responsabilidades por camada (models/services/routes), centralizar configuracao por ambiente e eliminar imports circulares nas rotas.

## Resultado Final (verificado)
- `app.py` foi reduzido para **98 linhas** (bootstrap/minimalista).
- A aplicacao responde com HTTP **200** em `http://127.0.0.1:5000/`.
- Modelos SQLAlchemy centralizados em `models/__init__.py` (**127 linhas**).
- Servicos de dominio centralizados em `services/`.
- Rotas organizadas em Blueprints em `routes/`.

## Estrutura Atual
```text
spotted-social/
  app.py                    # bootstrap: create_app, config, socketio, register blueprints
  config.py                 # configuracao centralizada (dotenv)
  extensions.py             # socketio e estado compartilhado
  .env.example              # template de variaveis de ambiente

  models/
    __init__.py             # db + classes SQLAlchemy

  services/
    __init__.py
    image_service.py        # processamento de imagem
    notification_service.py # notificacoes e mencoes
    feed_service.py         # regras de feed/eventos
    direct_service.py       # regras de direct/chat/socket
    startup_service.py      # init do banco + ensure_* schema
    template_service.py     # filtros/context processors/error handlers

  routes/
    auth.py                 # welcome/login/registro/logout
    admin.py                # toggle verificacao
    notifications.py        # denunciar/notificacoes/read
    public.py               # /public e socket.io js bridge
    feed.py                 # feed/search/posts/eventos
    perfil.py               # perfil/seguir/recado
    mural.py                # mural CRUD
    direct.py               # inbox/direct/conversa + APIs de grupos/mensagens
```

## O que foi movido por camada

### 1) Models (`models/`)
As classes SQLAlchemy foram centralizadas no pacote `models`:
- `User`, `Post`, `Comment`, `Notification`, `Message`
- `Conversation`, `ConversationMember`, `DirectChatMessage`, `MessageReaction`
- `Event`, `MuralPost`
- tabelas `followers`, `post_likes`
- `db` e helper `br_time()`

## 2) Services (`services/`)
A logica de negocio saiu das rotas e do app bootstrap:
- `services/image_service.py`
  - `save_and_optimize_image(...)`
- `services/notification_service.py`
  - `create_notification(...)`
  - `notify_mentions(...)`
  - `resolve_user_by_sender_name(...)`
- `services/feed_service.py`
  - pagina feed, normalizacoes e sincronizacao de evento no feed
- `services/direct_service.py`
  - regras de acesso/participacao em conversas, serializacao, unread, presenca, grupos
- `services/startup_service.py`
  - `initialize_database()` + `ensure_*` de schema
- `services/template_service.py`
  - filtros jinja, globals e handler global de erro

## 3) Blueprints (`routes/`)
Rotas remanescentes do antigo monolito foram distribuidas:
- `routes/auth.py`
- `routes/admin.py`
- `routes/notifications.py`
- `routes/public.py`
- e ajustes nos existentes: `feed.py`, `perfil.py`, `mural.py`, `direct.py`

## 4) Configuracao Centralizada
`config.py` agora concentra `app.config` com suporte a `.env`:
- Flask/DB (`SECRET_KEY`, `DATABASE_URL`)
- upload/static (`UPLOAD_FOLDER`, `PUBLIC_FOLDER`, `MAX_CONTENT_LENGTH`)
- direct (`DIRECT_ENABLED`)
- socketio (`SOCKETIO_*`)
- sessao/log (`SESSION_EXPIRE_DAYS`, `SPOTTED_ERROR_LOG`)

Arquivo de exemplo criado: `/.env.example`.

## 5) app.py Minimalista
O `app.py` agora faz apenas:
1. `create_app()`
2. carregar `Config`
3. inicializar `db` e `socketio`
4. registrar filtros/handlers de template
5. registrar blueprints
6. executar `initialize_database()` no app context
7. iniciar servidor no `__main__`

## Estrategia de Circular Imports (aplicada)
- `db` vem de `models` (fonte unica).
- `socketio` vem de `extensions`.
- rotas importam **models/services**, nao importam `app`.
- registro de blueprints e feito dentro de `_register_blueprints(app)`.
- services usam `current_app` quando precisam de config/log.
- `modules/models.py` mantido como wrapper de compatibilidade para migracao gradual.

## Compatibilidade durante migracao
Para evitar quebra imediata de `url_for(...)` legado sem prefixo de blueprint, `app.py` adiciona aliases de endpoint (ex.: `welcome`, `logout`, `direct_conversation`, etc.) apontando para os endpoints blueprint equivalentes.

## Validacao executada
### Compilacao Python
```powershell
python -m py_compile app.py routes\feed.py routes\perfil.py routes\mural.py routes\direct.py routes\auth.py routes\notifications.py routes\public.py routes\admin.py services\feed_service.py services\notification_service.py services\direct_service.py services\startup_service.py services\template_service.py models\__init__.py
```

### Smoke test HTTP
```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5000/" -TimeoutSec 5
```
Resultado observado: `StatusCode = 200`.

## Como rodar
```powershell
python app.py
```

## Checklist de migracao concluida
- [x] Modelos extraidos para `models/`
- [x] Services criados para logica complexa
- [x] Config centralizada em `config.py` + `.env.example`
- [x] Rotas remanescentes modularizadas em Blueprints
- [x] `app.py` minimalista
- [x] Estrategia anti-circular import aplicada

## Pontos de atencao (proximas melhorias)
- Migrar scripts/testes legados que ainda fazem `from app import ...` para importar de `models/`, `services/` e `extensions/`.
- Avaliar remoção futura do wrapper `modules/models.py` apos estabilizacao.
- Opcional: dividir `routes/direct.py` (ainda grande) em submodulos `routes/direct_http.py` e `routes/direct_socket.py`.

---

Se precisar, na proxima etapa eu aplico a limpeza final de compatibilidade (remocao dos aliases legados e do wrapper `modules/models.py`) com uma migração assistida dos testes/scripts.
