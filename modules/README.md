# 📦 MODULES - Estrutura Modular do Spotted Social

## 🎯 O que é?

A pasta `modules/` contém toda a lógica centralizada da aplicação Flask, separada da aplicação principal.

## 📁 Estrutura

```
modules/
├── __init__.py           # Exports públicos
├── config.py             # Configurações
├── models.py             # Models do banco de dados
└── helpers.py            # Funções auxiliares
```

---

## 🔌 Como Usar

### Importar Models
```python
from modules import User, Post, Event, db

# Usar
user = User.query.first()
```

### Importar Configurações
```python
from modules.config import get_config, get_feed_page_size

config = get_config()
page_size = get_feed_page_size()
```

### Importar Helpers
```python
from modules.helpers import (
    save_and_optimize_image,
    notify_mentions,
    users_follow_each_other
)

# Usar
filename = save_and_optimize_image(file)
```

---

## 📝 Arquivos Detalhes

### modules/config.py
Contém todas as configurações da aplicação:
- Variáveis de ambiente
- Configuração do banco de dados
- Configuração do SocketIO
- Validação de valores

**Funções principais:**
- `get_config()` - Dict com todas as configs
- `get_feed_page_size()` - Tamanho da página validado
- `get_socketio_async_mode()` - Modo async do SocketIO

### modules/models.py
Define todos os modelos do banco de dados:
- Tabelas (followers, post_likes)
- Classes de modelo (User, Post, Comment, etc.)
- Relacionamentos
- Função `br_time()` para timezone

**Modelos:**
- User
- Post
- Comment
- Notification
- Message
- Conversation
- ConversationMember
- DirectChatMessage
- MessageReaction
- Event
- MuralPost

### modules/helpers.py
Funções auxiliares reutilizáveis:
- Processamento de imagens
- Notificações
- Busca de usuários
- Verificação de seguimento

**Funções principais:**
- `save_and_optimize_image()` - Upload e conversão WebP
- `notify_mentions()` - Notifica menções
- `resolve_user_by_sender_name()` - Busca usuário
- `users_follow_each_other()` - Verifica seguimento mútuo

### modules/__init__.py
Exports centralizados para facilitar imports:
```python
from modules import User, Post, db
```

---

## 🚀 Começando

### Básico
```python
from modules import User, db

# Criar usuário
new_user = User(username='joao', password='hash')
db.session.add(new_user)
db.session.commit()

# Buscar usuário
user = User.query.filter_by(username='joao').first()
```

### Com Helpers
```python
from modules import User, db
from modules.helpers import notify_mentions, save_and_optimize_image

# Salvar imagem
filename = save_and_optimize_image(request.files['image'], 'user_pic')

# Notificar menções em post
notify_mentions(db, '@joao oi!", 'maria', post_id=1)
```

### Com Config
```python
from modules.config import get_config
from flask import Flask

app = Flask(__name__)
config = get_config()
app.config.update(config)
```

---

## 📚 Exemplo Completo

```python
from flask import Flask, request
from modules import User, Post, db
from modules.helpers import save_and_optimize_image, notify_mentions
from modules.config import get_config

app = Flask(__name__)
config = get_config()
app.config.update(config)

db.init_app(app)

@app.route('/criar-post', methods=['POST'])
def criar_post():
    content = request.form.get('content')
    user_id = session['user_id']
    
    # Processar imagem
    image_file = request.files.get('image')
    media_url = None
    if image_file:
        media_url = save_and_optimize_image(image_file, f'post_{user_id}')
    
    # Criar post
    post = Post(
        content=content,
        user_id=user_id,
        media_url=media_url
    )
    db.session.add(post)
    db.session.flush()
    
    # Notificar menções
    notify_mentions(db, content, User.query.get(user_id).username, post.id)
    
    db.session.commit()
    return redirect(url_for('feed'))
```

---

## 🔄 Futuro

### Phase 2: Blueprints
```
modules/
├── config.py
├── models.py
├── helpers.py
├── auth/
│   └── routes.py
├── feed/
│   └── routes.py
├── profile/
│   └── routes.py
└── direct/
    └── routes.py
```

### Phase 3: Services
```
modules/
├── services/
│   ├── user_service.py
│   ├── post_service.py
│   └── notification_service.py
└── handlers/
    └── socketio_handlers.py
```

---

## ❓ FAQ

**P: Por que modules/?**  
R: Melhor organização e clareza do que é modular vs. aplicação principal.

**P: Posso importar de modules.models diretamente?**  
R: Sim! `from modules.models import User` funciona igual `from modules import User`

**P: E o app.py?**  
R: Permanece com a inicialização da app, registro de blueprints e SocketIO.

**P: Como adiciono novo modelo?**  
R: Adicione em `modules/models.py` e exporte em `modules/__init__.py`

---

## 📚 Referências

- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy ORM: https://docs.sqlalchemy.org/
- Python Best Practices: https://pep8.org/

---

**Criado**: 19 de Abril de 2026  
**Versão**: 1.0  
**Manutentor**: Código refatorado


