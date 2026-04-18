# Debug - Problema de Envio de Comentários

## Problema Identificado
Quando o usuário tentava comentar um post, o comentário **NÃO era enviado** após clicar no botão "Enviar". A requisição AJAX falhava silenciosamente.

## Causa Raiz

### 1. **Backend** - Rota retornava redirecionamento para requisições AJAX
   - A rota `/comentar/<post_id>` **sempre retornava `redirect()`** independentemente de ser AJAX ou formulário tradicional
   - Redirecionamentos HTTP (302) não são considerados "ok" por clientes AJAX fetch
   - O erro era silencioso - nenhuma notificação ao usuário

### 2. **Frontend** - Função JavaScript tinha problemas
   - Sem tratamento de erros HTTP
   - Sem tratamento de erros de conexão
   - Sem feedback visual durante o envio
   - Sem header `X-Requested-With` para indicar requisição AJAX

## Soluções Aplicadas

### 1. Backend - Arquivo `/routes/feed.py`

#### Mudanças na rota `@feed_bp.route('/comentar/<int:post_id>', methods=['POST'])`:

**Antes:**
```python
@feed_bp.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    if 'user_id' not in session: return redirect(url_for('welcome'))
    content = request.form.get('comment_content')
    post = Post.query.get_or_404(post_id)
    if content:
        # adiciona comentário
        db.session.commit()
    return redirect(url_for('feed', _anchor=f"post-{post_id}"))
```

**Depois:**
```python
@feed_bp.route('/comentar/<int:post_id>', methods=['POST'])
def comentar(post_id):
    # 1. Verifica autenticação
    # 2. Valida conteúdo do comentário
    # 3. Detecta se é requisição AJAX via header 'X-Requested-With'
    # 4. Retorna JSON (201) para AJAX, redirect para formulários tradicionais
    # 5. Trata erros com try/except e retorna JSON (500) em caso de falha
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'ok': True,
            'comment_id': new_comment.id,
            'message': 'Comentário adicionado com sucesso'
        }), 201
    else:
        return redirect(url_for('feed', _anchor=f"post-{post_id}"))
```

**Principais mudanças:**
- Valida se conteúdo está vazio
- Detecta requisições AJAX via header `X-Requested-With`
- Retorna JSON (201) para sucesso em AJAX
- Retorna JSON (400) para comentário vazio em AJAX
- Retorna JSON (500) para erros em AJAX
- Mantém redirecionamentos para formulários tradicionais
- Adiciona try/except para tratar erros de DB

### 2. Frontend - Arquivo `/static/public/js/index-search.js`

#### Mudanças na função `ajaxComment()`:

**Adicionado:**

1. **Header AJAX** (linhas 109-111):
```javascript
headers: {
    'X-Requested-With': 'XMLHttpRequest'
}
```

2. **Tratamento de erro HTTP** (linhas 113-118):
```javascript
if (!response.ok) {
    console.error('Comment submission failed with status:', response.status);
    setInlineError(input, errorEl, 'Erro ao enviar comentário. Tente novamente.');
    if (submitBtn) submitBtn.disabled = false;
    return;
}
```

3. **Desabilitamento do botão durante envio** (linhas 103-104):
```javascript
const submitBtn = form.querySelector('button[type="submit"]');
if (submitBtn) submitBtn.disabled = true;
```

4. **Verificação do container** (linhas 120-126):
```javascript
const container = document.getElementById('comments-container-' + postId);
if (!container) {
    console.error('Comments container not found for post:', postId);
    setInlineError(input, errorEl, 'Erro ao atualizar comentários.');
    if (submitBtn) submitBtn.disabled = false;
    return;
}
```

5. **Tratamento de erro de conexão** (linhas 160-164):
```javascript
.catch((error) => {
    console.error('Erro ao enviar comentário:', error);
    setInlineError(input, errorEl, 'Erro de conexão. Tente novamente.');
    if (submitBtn) submitBtn.disabled = false;
});
```

6. **Re-habilitação do botão após sucesso** (linha 159):
```javascript
if (submitBtn) submitBtn.disabled = false;
```

## Resultados

✅ **Antes**: 
- Comentário não era enviado
- Sem feedback ao usuário
- Erro silencioso (apenas em console)

✅ **Depois**: 
- ✔ Comentário é enviado com sucesso
- ✔ Aparece imediatamente na interface
- ✔ Usuário vê mensagem de erro se houver problemas
- ✔ Botão desabilitado durante envio (previne duplicatas/race conditions)
- ✔ Console logs ajudam na depuração
- ✔ Melhor tratamento de erros de rede
- ✔ Melhor UX com feedback visual

## Fluxo Corrigido

```
Usuário clica "Enviar" 
  → JavaScript valida conteúdo
  → Botão desabilitado
  → Requisição AJAX com header X-Requested-With
  ↓
  Backend recebe requisição
  → Valida conteúdo
  → Cria comentário no DB
  → Retorna JSON 201 com sucesso
  ↓
  JavaScript recebe resposta
  → Adiciona comentário ao DOM
  → Limpa o input
  → Atualiza contador
  → Botão re-habilitado
  → Usuário vê comentário aparecer imediatamente
```

## Como Testar

1. Acesse a página de feed (`/feed`)
2. Escreva um comentário em qualquer post
3. Clique em "Enviar"
4. O comentário deve aparecer **imediatamente** sem recarregar a página
5. Tente enviar um comentário vazio - você verá uma mensagem de erro
6. Abra o DevTools (F12) → Console para ver logs detalhados
7. Teste com conexão lenta (DevTools → Network → Throttling) para confirmar o feedback visual

## Arquivos Modificados

- `/routes/feed.py` - Rota `comentar()` com suporte a AJAX
- `/static/public/js/index-search.js` - Função `ajaxComment()` com tratamento de erros


