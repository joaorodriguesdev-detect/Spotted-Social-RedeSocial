# RELATÓRIO - projeto spotted-social

Data: 2026-04-14

Resumo executivo
----------------
Relatório conciso do estado atual do projeto "spotted-social" (monolito Flask). O código é um app server-rendered com recursos de feed, eventos e Direct (chat) usando Flask-SocketIO. O repositório está funcional para desenvolvimento local, mas contém práticas que requerem melhorias antes de produção (seed admin com senha hardcoded, ausência de whitelist de uploads, sem migrações formais, CORS permissivo para SocketIO, etc.).

Estado atual — visão geral
--------------------------
- Código principal: `app.py` (monolito) — modelos, helpers, rotas principais e handlers do SocketIO.
- Blueprints parciais: `routes/feed.py`, `routes/perfil.py`, `routes/direct.py` (o app prefere `routes.direct` e faz fallback para `routes.direct_stub` se a import falhar).
- Templates Jinja em `templates/` e assets públicos em `static/public/`.
- Uploads de usuários armazenados em `static/uploads/`.
- Banco: Flask-SQLAlchemy com SQLite por padrão (`sqlite:///spotted.db`), configurável via `DATABASE_URL`.
- Testes: existe um teste de integração/end-to-end relacionado ao Direct em `tests/run_direct_all_read_test.py`.

Mudanças detectadas (em relação ao documento `AGENTS.md` original)
-----------------------------------------------------------------
Estas são as alterações ou pontos novos que o relatório detectou no código:

1. Otimização de imagens ao salvar
   - `app.py` introduziu `save_and_optimize_image(file_storage, filename_base, ...)`.
   - Quando a biblioteca Pillow (PIL) está disponível, o helper converte e redimensiona imagens para WebP, produzindo um nome final com extensão `.webp`. Em falha ou ausência do PIL ele faz fallback para salvar o arquivo original.
   - Endpoints que aceitam uploads (ex.: `postar`, `criar_evento`, `editar_perfil`) utilizam esse helper e normalmente passam um "filename base" (UUID) sem extensão.

2. Fallback do blueprint `routes.direct`
   - `app.py` tenta importar `routes.direct` e, em caso de erro, registra `routes.direct_stub` para permitir que a aplicação suba para debugging. Isso pode mascarar erros de importação no `routes/direct.py` durante desenvolvimento.

3. Novas variáveis de ambiente e runtime para SocketIO
   - `SOCKETIO_CORS_ALLOWED_ORIGINS`, `SOCKETIO_ALLOW_UPGRADES`, `SOCKETIO_ASYNC_MODE` foram adicionadas/consumidas para configurar comportamento do SocketIO.
   - O runner `if __name__ == '__main__'` agora respeita `FLASK_DEBUG`, `FLASK_RUN_HOST` e `PORT`.

4. Seed do usuário `admin`
   - O seeding automático do usuário `admin` permanece (senha hardcoded `Migo@2026!#`). A `display name` do admin foi alterada para `Spotted Social` no código que chamou a atenção.

5. Horário/tempo com tzinfo
   - `br_time()` agora retorna datetimes aware (timezone UTC-3). Algumas funções de formatação/relativo foram ajustadas para trabalhar com tz-aware datetimes.

6. Otimização da busca de usuários no Direct
   - `/api/direct/users` aplica filtro de mutual-follow usando uma expressão SQL (EXISTS) quando possível, e cai para filtragem em Python se o ambiente não suportar a expressão — isso altera como o LIMIT se comporta e é relevante ao testar e depurar.

Implicações práticas (para um agente/novo desenvolvedor)
-------------------------------------------------------
- Ao adicionar ou modificar endpoints que lidam com uploads, chame `save_and_optimize_image(...)` quando apropriado e leve em conta que o resultado pode ser um arquivo `.webp` (padrão ao usar PIL).
- Não conte com `routes/direct.py` sendo sempre o blueprint ativo — se `app.py` conseguir importar `routes.direct_stub` por causa de um erro, parte do comportamento pode estar reduzido. Corrija a origem do erro em `routes/direct.py` em vez de confiar no stub.
- Para testes de performance/tempo, trate datetimes como timezone-aware (BR UTC-3) para evitar discrepâncias.

Arquitetura técnica (pontos-chave)
----------------------------------
- Modelos (em `app.py`): `User`, `Post`, `Comment`, `Notification`, `Message`, `Event`, `Conversation`, `ConversationMember`, `DirectChatMessage`, `MessageReaction`.
- Helpers críticos (em `app.py`): `get_feed_chunk`, `annotate_posts_with_like_info`, `build_event_post_content`, `sync_event_feed_post`, `save_and_optimize_image`, `ensure_group_conversation`, `get_or_create_dm_conversation`, `mark_conversation_read`, `build_direct_inbox_items`.
- Rotas importantes: `/`, `/feed`, `/feed/more`, `/postar`, `/criar_evento`, `/editar_evento`, `/eventos`, `/direct`, `/direct/conversa/<username>`, `/api/direct/*` endpoints.
- SocketIO: eventos `direct:message`, `direct:typing`, `direct:presence`, `direct:members-updated`, `notification:new`, etc., emitidos a salas por conversation id e por usuário (`user:<id>`).

Segurança & riscos prioritários
-------------------------------
- Admin seed com senha hardcoded — risco alto para produção. Recomenda-se remover o seeding automático ou ler `ADMIN_PASSWORD` do ambiente.
- Ausência de whitelist de extensões/validação de conteúdo de upload — risco de upload de arquivos arbitrários. Mesmo com a conversão WebP, validar tipo e cabeçalho do arquivo é necessário.
- Sem CSRF para formulários — adiciona vulnerabilidade em endpoints POST.
- SocketIO CORS permissivo por padrão — revisar `SOCKETIO_CORS_ALLOWED_ORIGINS` antes do deploy.
- Ausência de migrações formais (dependência de `db.create_all()` e `ALTER TABLE` runtime) — arriscado para atualizações repetíveis.
- Rate limiting ausente — adicionar proteção para login/APIs sensíveis.

Como executar localmente (rápido)
---------------------------------
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
--------------------------------------------------
- `DATABASE_URL` (ex: `sqlite:///spotted.db`)
- `SECRET_KEY`
- `FEED_PAGE_SIZE` (valores permitidos: `6`, `8`, `12`)
- `DIRECT_ENABLED` (True/False — app força `True` por padrão no código atual)
- `SOCKETIO_CORS_ALLOWED_ORIGINS`, `SOCKETIO_ALLOW_UPGRADES`, `SOCKETIO_ASYNC_MODE`
- `FLASK_DEBUG`, `FLASK_RUN_HOST`, `PORT` (para runner local)

Recomendações acionáveis (prioridade alta → baixa)
--------------------------------------------------
1. Remover/parametrizar o seeding do admin (ler senha de `ADMIN_PASSWORD` ou exigir criação manual em dev).
2. Adicionar whitelist de extensões e validação do conteúdo de uploads (usar Pillow para checar headers/abrir imagens).
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

