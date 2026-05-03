# RELATÓRIO - projeto spotted-social

Data: 2026-04-19

Resumo executivo
----------------
Relatório conciso do estado atual do projeto "spotted-social" (monolito Flask). O código é um app server-rendered com recursos de feed, eventos e Direct (chat) usando Flask-SocketIO. O repositório está funcional para desenvolvimento local, mas contém práticas que requerem melhorias antes de produção (seed admin com senha hardcoded, ausência de whitelist de uploads, sem migrações formais, CORS permissivo para SocketIO, etc.).

Estado atual — visão geral
--------------------------
- Código principal: `app.py` agora age principalmente como fábrica da aplicação — configura logger, registra blueprints, inicializa `SocketIO` e delega modelos e helpers para os pacotes `models/` e `services/`.
- Models estão em `models/__init__.py` (por exemplo `User`, `Post`, `Comment`, `Notification`, `Event`, `Conversation`, `ConversationMember`, `DirectChatMessage`, `MessageReaction`).
- Helpers e lógica de domínio foram centralizados em `services/` (ex.: `services/feed_service.py`, `services/direct_service.py`, `services/image_service.py`, `services/startup_service.py`).
- Rotas HTTP estão organizadas como blueprints em `routes/` (ex.: `routes/feed.py`, `routes/perfil.py`, `routes/direct.py`, `routes/mural.py`, `routes/admin.py`, `routes/auth.py`, `routes/notifications.py`, `routes/public.py`).
- Templates Jinja em `templates/`.
- User uploads ficam em `static/uploads/`; assets públicos em `static/public/`.
- DB é Flask-SQLAlchemy com SQLite por padrão (`sqlite:///spotted.db`), overridable via `DATABASE_URL`.
- Testes: existe um teste end-to-end relacionado ao Direct em `tests/run_direct_all_read_test.py`.

Mudanças detectadas (observações relevantes)
-----------------------------------------
1. Otimização de imagens ao salvar
   - Implementado em `services/image_service.py` (função `save_and_optimize_image(...)`).
   - Quando Pillow (PIL) está disponível, o helper converte/normaliza e salva em WebP (retornando um nome com extensão `.webp`). Se Pillow não estiver presente ou ocorrer erro, há fallback que salva o arquivo original.
   - Rotas que aceitam uploads (por exemplo em `routes/feed.py` e `routes/perfil.py`) chamam esse helper e normalmente usam um base name (UUID) sem extensão.

2. Blueprint `routes.direct` está registrado diretamente
   - `app.py` importa e registra `routes.direct` diretamente (não há fallback automático para `routes.direct_stub` na versão atual). Se `routes.direct` falhar ao importar, a aplicação irá falhar no startup — o que é preferível para detectar problemas de importação durante o desenvolvimento.

3. Variáveis de ambiente / runtime para SocketIO
   - `SOCKETIO_CORS_ALLOWED_ORIGINS`, `SOCKETIO_ALLOW_UPGRADES`, `SOCKETIO_ASYNC_MODE` são consultadas pela inicialização do SocketIO em `app.create_app()`.

4. Seed do usuário `admin`
   - `services/startup_service.initialize_database()` cria (quando ausente) um usuário `admin` com senha hardcoded `Migo@2026!#` e nome exibido `Spotted Social`. Isto facilita desenvolvimento local, mas é um risco se o comportamento permanecer em produção.

5. `br_time()` e timestamps
   - `br_time()` está definido em `models/__init__.py` e retorna `datetime.now() - timedelta(hours=3)` (UTC-3) — valor sem tzinfo (datetime "naive"). Algumas partes do código tratam explicitamente de compatibilidade caso datetimes com tzinfo apareçam.

6. Busca de usuários no Direct
   - `/api/direct/users` tenta aplicar o filtro de mutual-follow no nível do banco (usando EXISTS) para que o LIMIT seja aplicado após a filtragem. Caso o ambiente SQL não suporte a expressão usada, há um fallback que busca mais resultados e filtra em Python.

Implicações práticas (para desenvolvedores)
------------------------------------------
- Ao modificar endpoints de upload, use `save_and_optimize_image(...)` em `services/image_service.py` para aproveitar a otimização WebP quando Pillow estiver disponível. Lembre-se que o nome retornado pode terminar em `.webp`.
- Corrija erros diretamente em `routes/direct.py` em vez de depender de qualquer fallback — o app registra `routes.direct` explicitamente.
- `br_time()` produz datetimes UTC-3 sem tzinfo; trate conversões e comparações de datas com cuidado ao integrar sistemas externamente sensíveis a timezone.

Arquitetura técnica (pontos-chave)
---------------------------------
- Models: `models/__init__.py` — `User`, `Post`, `Comment`, `Notification`, `Event`, `MuralPost`, `Conversation`, `ConversationMember`, `DirectChatMessage`, `MessageReaction`, e helpers como `br_time()`.
- Services: helpers e regras do domínio em `services/`:
  - `services/feed_service.py` — `get_feed_chunk`, `annotate_posts_with_like_info`, `build_event_post_content`, `sync_event_feed_post`, `parse_event_datetime`, etc.
  - `services/direct_service.py` — helpers para conversas, membros, marcação de leitura e lógica de disponibilidade do Direct.
  - `services/image_service.py` — `save_and_optimize_image` (Pillow-aware WebP conversion + fallbacks).
  - `services/startup_service.py` — inicialização DB, `db.create_all()` e helpers `ensure_*` com `ALTER TABLE` quando necessário.
- Rotas: blueprints em `routes/` cobrindo feed, perfil, direct, mural, notificações, admin, auth e arquivos públicos.
- Real-time: `Flask-SocketIO` é inicializado em `app.create_app()` e utilizado por handlers em `routes/direct.py`.

Segurança & riscos prioritários
------------------------------
- Seed do admin com senha hardcoded — risco alto para produção. Recomenda-se ler `ADMIN_PASSWORD` do ambiente ou remover o seed no deploy.
- Ausência de migrações formais: o projeto usa `db.create_all()` e `ALTER TABLE` ad-hoc — trocar para Alembic / Flask-Migrate para atualizações repetíveis.
- Validação de uploads: não há whitelist de extensões/validação robusta do conteúdo de upload. Mesmo com a conversão WebP, prefira validar headers (Pillow) e checar extensões permitidas.
- CSRF para formulários POST ausente — adicione proteção (Flask-WTF ou solução equivalente).
- Cookies de sessão não endurecidos por configuração (Secure/HttpOnly/SameSite) — configure em produção.
- SocketIO CORS permissivo por padrão (config por `SOCKETIO_CORS_ALLOWED_ORIGINS`) — restrinja em produção.
- Rate limiting ausente — adicione proteção em endpoints sensíveis (login, APIs públicas).

Observações sobre scripts e testes
---------------------------------
- Scripts em `scripts/` incluem `check_feed.py` e `convert_uploads_to_webp.py` (úteis para manutenção local/otimização). Esses scripts podem modificar `instance/spotted.db` — use cópias ao testar.
- Teste end-to-end para Direct: `tests/run_direct_all_read_test.py` (usa `instance/spotted.db`).
- Há duplicação de utilitários em `modules/helpers.py` (incluindo uma versão de `save_and_optimize_image`) — prefira a implementação em `services/image_service.py` para consistência.

Como executar localmente (rápido)
--------------------------------
- Rodar app em dev:

```powershell
python app.py
```

- Verificar sintaxe do app:

```powershell
python -m py_compile app.py
```

- Rodar o teste Direct (end-to-end, altera `instance/spotted.db`):

```powershell
python -u tests/run_direct_all_read_test.py
```

Variáveis de ambiente úteis (observadas no código)
------------------------------------------------
- `DATABASE_URL` (ex: `sqlite:///spotted.db`)
- `SECRET_KEY`
- `FEED_PAGE_SIZE` (valores permitidos: `6`, `8`, `12`)
- `DIRECT_ENABLED` (True/False — app fornece True por padrão)
- `SOCKETIO_CORS_ALLOWED_ORIGINS`, `SOCKETIO_ALLOW_UPGRADES`, `SOCKETIO_ASYNC_MODE`
- `FLASK_DEBUG`, `FLASK_RUN_HOST`, `PORT` (runner local)

Recomendações acionáveis (prioridade alta → baixa)
------------------------------------------------
1. Remover/parametrizar o seeding do admin (ler senha de `ADMIN_PASSWORD` ou exigir criação manual em dev).
2. Adicionar whitelist de extensões e validação com Pillow para uploads (pequena mudança em `services/image_service.py` e nas rotas que salvam arquivos).
3. Introduzir migrações formais (Alembic / Flask-Migrate) e parar de usar ALTER TABLE ad-hoc no import.
4. Adicionar CSRF protection (Flask-WTF ou similar) para formulários POST.
5. Configurar `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` no `app.config` quando em produção.
6. Restringir `SOCKETIO_CORS_ALLOWED_ORIGINS` em produção.
7. Adicionar rate limiting (Flask-Limiter) em endpoints de autenticação e APIs.

Change Safety Notes
-------------------
- Tenha cuidado ao editar inicialização em `app.py`; side effects ocorrem em tempo de import (DB creation, schema helpers, admin seed).
- Ao alterar o formato do texto de evento, atualize tanto o produtor quanto o parser (o feed mirror usa o marcador `📢 NOVO EVENTO:`).
- Mantenha rotas e templates em sincronia; o sistema é fortemente acoplado por variáveis de contexto usadas pelas views.
- Scripts em `scripts/` e testes em `tests/` podem modificar `instance/spotted.db`. Trabalhe em cópias quando for necessário.

Mudanças que eu já apliquei ao repositório
------------------------------------------
- Atualizei `AGENTS.md` com pequenas notas cirúrgicas para refletir: o helper de otimização (`save_and_optimize_image`) agora centralizado em `services/image_service.py`, a configuração do SocketIO e observações sobre o seed do `admin`.

Próximos passos sugeridos (posso implementar)
--------------------------------------------
- Atualizar `README.md` para documentar a otimização WebP e a dependência opcional Pillow.
- Implementar whitelist básica de uploads e validação com Pillow (pequena mudança em `services/image_service.py` nas rotas que salvam arquivos).
- Tornar a senha do admin dependente de `ADMIN_PASSWORD` ou remover o seed em produção.

-----
Arquivo gerado automaticamente com base no estado dos arquivos do repositório no momento desta execução.

3. Introduzir migrações formais (Alembic / Flask-Migrate) e parar de usar ALTER TABLE ad-hoc no import.
4. Adicionar CSRF protection (Flask-WTF ou similar) para formulários POST.
5. Configurar `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE` no `app.config` quando em produção.
6. Restringir `SOCKETIO_CORS_ALLOWED_ORIGINS` em produção.
7. Adicionar rate limiting (Flask-Limiter) em endpoints de autenticação e APIs.

Mudanças que eu já apliquei ao repositório
------------------------------------------
- Atualizei `AGENTS.md` com pequenas notas cirúrgicas para refletir: o helper de otimização (`save_and_optimize_image`), o fallback do blueprint `routes.direct` para `routes.direct_stub`, e as variáveis de ambiente de SocketIO. (O arquivo `AGENTS.md` foi preservado na sua maior parte; apenas acrescentei observações pontuais.)

Próximos passos sugeridos (posso implementar)
--------------------------------------------
- Atualizar `README.md` para documentar a otimização WebP e a dependência opcional Pillow.
- Implementar whitelist básica de uploads e validação com Pillow (pequena mudança em `app.py` nas rotas que salvam arquivos).
- Tornar a senha do admin dependente de `ADMIN_PASSWORD` ou remover o seed em produção.

Se desejar, eu posso abrir um PR com qualquer uma das mudanças acima. Diga qual das ações prefere que eu implemente primeiro.


-----
Arquivo gerado automaticamente com base no estado dos arquivos do repositório no momento desta execução.

