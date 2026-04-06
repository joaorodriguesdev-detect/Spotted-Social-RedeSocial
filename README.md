# Spotted

Spotted é uma aplicação monolítica Flask (Python) com renderização server-side usando Jinja2. Ela implementa feed, eventos, mensagens diretas (conversas 1:1 e em grupo) e notificações em tempo real usando Flask-SocketIO.

Este repositório é destinado a desenvolvimento local e prototipagem — verifique as notas de segurança antes de qualquer deploy público.

## Pré-requisitos

- Python 3.10+ (ou a versão usada no projeto)
- Instalar dependências:

```powershell
pip install -r requirements.txt
```

## Rodando localmente

No diretório do projeto:

```powershell
# inicia o servidor em dev (usa config hardcoded em app.py por padrão)
python app.py
```

A aplicação roda por padrão em http://127.0.0.1:5000

## Variáveis de ambiente importantes

- `DATABASE_URL` — string de conexão para o banco (ex.: `sqlite:///spotted.db`). Se não definida, usa `sqlite:///spotted.db` por padrão.
- `SECRET_KEY` — chave de sessão/CSRF. Troque para um valor seguro em produção.
- `FEED_PAGE_SIZE` — controla a paginação do feed; valores permitidos: `6`, `8`, `12` (qualquer outro cai para `8`).
- (opcional) `ADMIN_PASSWORD` — recomendado: use para substituir o seed de admin em vez do valor hardcoded no código.

## Nota importante sobre admin seed

Por conveniência o arquivo `app.py` pode criar automaticamente um usuário `admin` com uma senha hardcoded quando o banco não contém um admin. Isto facilita testes locais, mas é perigosíssimo para produção. Antes de deploy:

- Remova ou comente o seeding automático, ou
- Troque para ler a senha a partir de uma variável de ambiente e exija alteração imediata do password.

## Uploads e segurança de arquivos

- Uploads de usuários são gravados em `static/uploads/` com nomes UUID.
- Recomendamos adicionar uma whitelist de extensões aceitas (ex.: `.jpg`, `.jpeg`, `.png`, `.gif`) e validar o conteúdo do arquivo (p. ex. usando Pillow para verificar headers de imagens) antes de salvar.

## Segurança e produção-hardening (resumo)

Antes de expor publicamente, trate estes itens:

- Substitua o admin seed por uma variável de ambiente ou remova-o.
- Adicione CSRF protection (Flask-WTF CSRF ou equivalente) nas rotas de POST.
- Configure cookies de sessão: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'` ou `Strict` conforme apropriado.
- Restrinja `cors_allowed_origins` do SocketIO em produção (não `*`).
- Adicione rate limiting (Flask-Limiter) em endpoints públicos sensíveis (login, APIs).
- Use migrações (Alembic / Flask-Migrate) em vez de `db.create_all()` + runtime ALTERs.

## Tests

Nenhum teste automatizado está presente atualmente no repositório root. Recomendamos adicionar testes unitários e de integração (pytest) cobrindo autenticação, posting, criação/edição de eventos, e fluxos de mensagens diretas.

## Patches recomendados (candidatos fáceis)

- Atualizar a mensagem de erro de "mutual-follow" quando tentar adicionar alguém a um grupo (local: `app.py`, rota `/api/direct/conversations/<id>/members`).
- Adicionar verificação de `ALLOWED_EXTENSIONS` no upload de imagens.
- Tornar o admin seed dependente de `ADMIN_PASSWORD` env var.

## Como contribuir

1. Fork e branch para sua feature/fix.
2. Abra um PR descrevendo a mudança e o motivo.
3. Adicione testes quando possível.

---

Se quiser, posso abrir um PR com pequenas mudanças: (a) atualizar a mensagem de mutual-follow, (b) adicionar `ALLOWED_EXTENSIONS` e validação mínima, e (c) implementar leitura da senha de admin via variável de ambiente.

