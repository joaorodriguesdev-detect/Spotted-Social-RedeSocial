# Spotted

Spotted é uma aplicação monolítica Flask (Python) com renderização server-side usando Jinja2. Ela implementa feed, eventos, mensagens diretas (conversas 1:1 e em grupo) e notificações em tempo real usando Flask-SocketIO.

Este repositório destina-se a desenvolvimento local e prototipagem — verifique as notas de segurança antes de qualquer deploy público.

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
- `ADMIN_PASSWORD` — (recomendado) se definido, será usado pelo seeding/seed inicial do admin em vez do valor hardcoded. Configure em ambientes de desenvolvimento para evitar senhas públicas.

Exemplo (PowerShell):

```powershell
$env:ADMIN_PASSWORD = 'troque_essa_senha_para_dev'
$env:SECRET_KEY = 'uma_chave_secreta_local'
python app.py
```

## Nota importante sobre o admin seed

Por conveniência o arquivo `app.py` pode criar automaticamente um usuário `admin` com uma senha hardcoded quando o banco não contém um admin. Isto facilita testes locais, mas é perigoso para produção. Antes de deploy em qualquer ambiente público:

- Remova ou comente o seeding automático; ou
- Certifique-se de definir `ADMIN_PASSWORD` via variável de ambiente e rotacionar a senha imediatamente.

Se quiser desabilitar o seeding em ambientes automatizados, exporte uma variável como `DISABLE_ADMIN_SEED=1` (implemente na sua implantação) ou modifique `app.py` para condicionalmente pular o seed.

## Uploads e segurança de arquivos

- Uploads de usuários são gravados em `static/uploads/` com nomes UUID.
- Recomendamos adicionar uma whitelist de extensões aceitas e validação do conteúdo do arquivo antes de salvar. Por exemplo, permitir somente: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`.
- Valide imagens usando Pillow (verifique headers) e limite o tamanho via `Config.MAX_CONTENT_LENGTH`.

Exemplo mínimo (conceitual) para ALLOWED_EXTENSIONS em `config.py` / validação de upload:

```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

def allowed_filename(filename):
	ext = os.path.splitext(filename.lower())[1]
	return ext in ALLOWED_EXTENSIONS
```

## Segurança e production-hardening (resumo)

Antes de expor publicamente, trate estes itens:

- Substitua o admin seed por uma variável de ambiente ou remova-o.
- Adicione CSRF protection (Flask-WTF CSRF ou equivalente) nas rotas de POST.
- Configure cookies de sessão: `SESSION_COOKIE_SECURE=True`, `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE='Lax'` ou `Strict` conforme apropriado.
- Restrinja `cors_allowed_origins` do SocketIO em produção (não `*`).
- Adicione rate limiting (Flask-Limiter) em endpoints públicos sensíveis (login, APIs).
- Use migrações (Alembic / Flask-Migrate) em vez de `db.create_all()` + runtime ALTERs.

Outras recomendações rápidas:

- Não exponha a base de dados SQLite em produção; use um RDBMS adequado e configure backups.
- Revise uploads e execute verificações de conteúdo/antivírus em pipelines de CI quando aplicável.

## Tests e scripts úteis

Existem alguns scripts e testes básicos no repositório:

- Test end-to-end Direct (usa Flask test client / SocketIO):

```powershell
python -u tests/run_direct_all_read_test.py
```

- Testes e utilitários existentes (ex.: `tests/test_image_uploads.py`, `scripts/check_feed.py`, `scripts/convert_uploads_to_webp.py`). Execute testes unitários (quando houver) com pytest:

```powershell
pip install pytest
pytest -q
```

---