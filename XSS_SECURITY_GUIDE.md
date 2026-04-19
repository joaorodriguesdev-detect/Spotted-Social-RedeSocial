# 🔐 Guia de Segurança XSS - Spotted Social

## Vulnerabilidades Detectadas e Correções Aplicadas

### 1. **Direct HTML Injection (8 vulnerabilidades altas)**

#### Problema
O projeto havia 8 pontos potenciais de XSS onde conteúdo gerado por usuários poderia injetar HTML/JavaScript malicioso.

#### Solução Implementada no Mural
```python
from markupsafe import escape

def sanitize_input(text):
    """Sanitize user input by escaping HTML special characters."""
    if not text:
        return ''
    clean_text = str(text).strip()[:1000]
    return escape(clean_text)
```

**Aplicação:**
- ✅ Todos os campos de entrada (`title`, `content`, `contact_info`)
- ✅ Realizado no backend ANTES de salvar no banco
- ✅ Não relied em template auto-escaping sozinho

---

### 2. **Análise de Rotas Vulneráveis**

#### `routes/feed.py`
**Vulneráveis:**
- ❌ `POST /feed/postar` - campo `content` sem sanitização
- ❌ `POST /feed/comentar` - campo `comment_content` sem sanitização

**Recomendação:**
```python
from markupsafe import escape

@feed_bp.route('/postar', methods=['POST'])
def postar():
    content = request.form.get('content', '')
    clean_content = escape(content.strip())[:5000]  # Sanitize!
    # ... rest of code
```

#### `routes/perfil.py`
**Vulneráveis:**
- ❌ `POST /editar_perfil` - campo `bio` sem sanitização
- ❌ `POST /enviar_recado` - campo `content` sem sanitização

**Recomendação:**
```python
@perfil_bp.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    bio = escape(request.form.get('bio', '').strip())[:150]
    # ... rest of code
```

#### `app.py` - Direct Messaging
**Vulneráveis:**
- ❌ `POST /api/direct/conversations/<id>/messages` - campo `content`

**Current Code:**
```python
content = (payload.get('content') or '').strip()  # NOT sanitized!
```

**Recommended:**
```python
from markupsafe import escape
content = escape((payload.get('content') or '').strip())[:500]
```

---

### 3. **Jinja2 Template Filter Review**

#### `@app.template_filter('mention')`
**Current Implementation:**
```python
@app.template_filter('mention')
def mention_filter(text):
    def replace_mention(match):
        username = match.group(1).lower()
        exists = User.query.filter_by(username=username).first()
        if exists:
            # ⚠️ UNSAFE: username not escaped!
            return f'<a href="/perfil/{username}" ...>@{username}</a>'
        return f'@{username}'
    return re.sub(r'@(\w+)', replace_mention, text)
```

**Recommendation:**
```python
from markupsafe import Markup, escape

@app.template_filter('mention')
def mention_filter(text):
    def replace_mention(match):
        username = match.group(1).lower()
        exists = User.query.filter_by(username=username).first()
        if exists:
            safe_username = escape(username)  # ✅ Escape username!
            return f'<a href="/perfil/{safe_username}" class="...">@{safe_username}</a>'
        return escape(f'@{username}')  # ✅ Escape if not found too
    # Process text first
    safe_text = escape(text)
    # Then apply mentions on escaped text
    result = re.sub(r'@(\w+)', replace_mention, str(safe_text))
    return Markup(result)  # Mark as safe for rendering
```

---

### 4. **Mentions in Templates**

#### Safe Pattern (✅ Current Implementation)
```jinja2
<p>Posted by @{{ post.author.username }}</p>
```
✅ Jinja2 auto-escapes by default

#### Unsafe Pattern (❌ Avoid)
```jinja2
<p>{{ post.author.bio | safe }}</p>
```
❌ Never use `| safe` with user-generated content!

#### Correct Pattern (✅ Recommended)
```jinja2
{% if post.author %}
<p>
    <a href="/perfil/{{ post.author.username | escape }}">
        @{{ post.author.username }}
    </a>
</p>
{% endif %}
```

---

### 5. **Sanitization Strategy by Field**

#### User-Generated Text
**Fields:** `bio`, `content`, `comment_content`, `title`, `contact_info`

**Strategy:**
```python
from markupsafe import escape

sanitized = escape(user_input.strip())[:max_length]
```

#### Usernames
**Fields:** `username`

**Strategy:**
```python
# Usernames already validated in registration
# But escape when rendering mentions
safe_username = escape(username)
```

#### URLs/Links
**Fields:** `profile_pic`, `media_url`

**Strategy:**
```python
# Must be validated path (UUID or deterministic)
# Validate format before accepting
import os
import uuid

allowed_folder = 'static/uploads'
filename = 'pfp_user_123.webp'
filepath = os.path.join(allowed_folder, filename)
# Validate path doesn't escape folder
if os.path.abspath(filepath).startswith(os.path.abspath(allowed_folder)):
    return send_file(filepath)
```

---

### 6. **Attack Scenarios & Mitigations**

#### Scenario 1: Comment Injection
```
User Input:
<img src=x onerror="alert('XSS')">

Without Sanitization:
<div>{{ comment }}</div>  → <div><img src=x onerror="alert('XSS')"></div>
                             ❌ Script executes!

With Sanitization:
<div>{{ comment | escape }}</div>  → <div>&lt;img src=x onerror="alert('XSS')"&gt;</div>
                                    ✅ Rendered as text!
```

#### Scenario 2: Mention Exploitation
```
User Input:
@<script>alert('XSS')</script>

Without Sanitization:
{{ post.author.bio | mention }}  → <a href="/perfil/<script>">...
                                    ❌ Script in href!

With Sanitization:
{{ post.author.bio | mention }}  → <a href="/perfil/&lt;script&gt;">...
                                    ✅ Escaped properly!
```

#### Scenario 3: Direct Message Injection
```
API Input:
{"content": "<iframe src='malicious.com'></iframe>"}

Without Sanitization:
{{ message.content }}  → <iframe src='malicious.com'></iframe>
                        ❌ Iframe loaded!

With Sanitization:
{{ message.content | escape }}  → &lt;iframe src='malicious.com'&gt;&lt;/iframe&gt;
                                  ✅ Text rendered!
```

---

### 7. **Implementation Checklist**

#### Phase 1: Immediate (Already Done for Mural)
- [x] Add `sanitize_input()` function to module
- [x] Apply to all text input routes
- [x] Add validation checks

#### Phase 2: Short-term (Recommended for Feed/Direct)
- [ ] Update `routes/feed.py` with sanitization
- [ ] Update `routes/perfil.py` with sanitization  
- [ ] Update Direct messaging routes
- [ ] Add unit tests for sanitization

#### Phase 3: Medium-term (Additional Security)
- [ ] Implement CSP (Content Security Policy) headers
- [ ] Add CSRF protection (Flask-WTF)
- [ ] Rate limiting on form submissions
- [ ] Audit logging of user inputs

#### Phase 4: Long-term (Enterprise)
- [ ] Web Application Firewall (WAF)
- [ ] Security audit by third party
- [ ] Penetration testing
- [ ] Bug bounty program

---

### 8. **Testing XSS Protections**

#### Unit Test Example
```python
from app import sanitize_input

def test_xss_protection():
    # Test HTML escape
    assert sanitize_input("<script>alert('xss')</script>") == \
           "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
    
    # Test quote escaping
    assert sanitize_input('"><script>alert("xss")</script>') == \
           '&quot;&gt;&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
    
    # Test attribute escape
    assert sanitize_input('x" onload="alert(1)') == \
           'x&quot; onload=&quot;alert(1)'
    
    # Test length limit
    assert len(sanitize_input("x" * 2000)) <= 1000
```

#### Manual Testing
1. Create post with: `<img src=x onerror="alert('XSS')">`
2. Verify no alert appears
3. Verify text rendered literally

---

### 9. **Best Practices Summary**

✅ **DO:**
- Sanitize at input time, not output time
- Use `markupsafe.escape()` for text content
- Validate user input format (regex, length, charset)
- Use allowlists for categories/enums
- Test with OWASP XSS payloads
- Log security events

❌ **DON'T:**
- Use `| safe` filter with user data
- Rely solely on HTML escaping
- Trust client-side validation
- Store unsanitized HTML
- Use `eval()` or `exec()`
- Concatenate strings for URLs

---

### 10. **References**

- OWASP Top 10: https://owasp.org/www-project-top-ten/
- XSS Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- MarkupSafe Docs: https://markupsafe.palletsprojects.com/
- Flask Security: https://flask.palletsprojects.com/en/latest/security/

---

## Implementação no Projeto Spotted-Social

### Mudanças Realizadas

#### ✅ Mural Module (`routes/mural.py`)
```python
from markupsafe import escape

def sanitize_input(text):
    if not text:
        return ''
    clean_text = str(text).strip()[:1000]
    return escape(clean_text)

# Applied to: title, content, contact_info
```

### Recomendações para Próximas Fases

1. **Feed Module:** Aplicar mesma sanitização em posts/comments
2. **Direct Module:** Sanitizar mensagens em tempo real
3. **Profile Module:** Sanitizar bio e nomes
4. **Tests:** Adicionar suite de testes XSS
5. **Documentation:** Manter este guia atualizado

---

**Documento atualizado em:** 18/04/2026  
**Versão:** 1.0  
**Status:** Implementado para Mural, Pendente para outras rotas

