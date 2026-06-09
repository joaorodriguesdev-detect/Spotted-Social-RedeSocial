# Spotted Social 

> **Rede Social Universitária** — Conecte-se, compartilhe e descubra o que está rolando na sua faculdade.

**Spotted Social** é uma plataforma de rede social desenvolvida para o ambiente universitário, permitindo que alunos publiquem "spotteds" (postagens anônimas ou identificadas), interajam com o feed, participem de eventos, criem anúncios no mural, conversem em tempo real e muito mais.

---

## ⚠️ Aviso Importante

> **🔒 API Privada**  
> Esta aplicação possui uma **API privada**. O backend FastAPI **não é público** e não deve ser exposto diretamente à internet sem camadas de segurança adicionais (proxy reverso, autenticação, rate limiting, etc.). O acesso à API é feito exclusivamente através do frontend Next.js, que atua como proxy (via `rewrites`) ou via chamadas autenticadas com JWT armazenado em cookies httpOnly.

---

## 📋 Índice

- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Backend — FastAPI](#backend--fastapi)
  - [Estrutura do Backend](#estrutura-do-backend)
  - [Modelos de Dados](#modelos-de-dados)
  - [Rotas / Endpoints](#rotas--endpoints)
  - [WebSocket](#websocket)
  - [Autenticação](#autenticação)
  - [Chatbot Spottinho (IA)](#chatbot-spottinho-ia)
- [Frontend — Next.js](#frontend--nextjs)
  - [Estrutura do Frontend](#estrutura-do-frontend)
  - [Componentes](#componentes)
  - [Contextos (Estado Global)](#contextos-estado-global)
  - [Hooks Personalizados](#hooks-personalizados)
  - [Middleware de Autenticação](#middleware-de-autenticação)
- [Como Executar o Projeto](#como-executar-o-projeto)
  - [Pré-requisitos](#pré-requisitos)
  - [Backend](#backend)
  - [Frontend](#frontend)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Deploy](#deploy)
- [Funcionalidades](#funcionalidades)
- [Contribuição](#contribuição)
- [Licença](#licença)

---

## 🏗️ Arquitetura

O projeto segue uma arquitetura **monorepo** com dois componentes principais:

```
spottedosocial_v4/
├── backend_fastapi/      # API Backend (Python / FastAPI)
│   ├── main.py           # Entry point da aplicação FastAPI
│   ├── config.py         # Configurações via pydantic-settings
│   ├── database.py       # Configuração do SQLAlchemy assíncrono
│   ├── dependencies.py   # Dependências de autenticação (JWT, CSRF)
│   ├── models/           # Modelos ORM (SQLAlchemy)
│   ├── routes/           # Rotas da API (APIRouters)
│   ├── schemas/          # Schemas Pydantic (validação request/response)
│   ├── services/         # Serviços (imagem, senha, segurança, socket, etc.)
│   ├── alembic/          # Migrations (Alembic)
│   └── requirements.txt  # Dependências Python
│
├── frontend/             # Frontend (Next.js 14)
│   ├── src/
│   │   ├── app/          # App Router (páginas e layouts)
│   │   ├── components/   # Componentes React reutilizáveis
│   │   ├── context/      # Contextos de estado global (Auth, Post, WebSocket)
│   │   ├── hooks/        # Hooks personalizados (useChat, useFeed, etc.)
│   │   ├── lib/          # Utilitários (API client, auth-token, api-base)
│   │   └── types/        # Tipos TypeScript (interfaces)
│   ├── next.config.js    # Configuração do Next.js (rewrites, imagens)
│   └── package.json      # Dependências Node.js
│
├── README.md             # Este arquivo
└── .gitignore            # Regras de git ignore
```

### Fluxo de Dados

```
[Usuário] → [Next.js (Frontend)] → [Proxy Rewrite] → [FastAPI (Backend)] → [SQLite/PostgreSQL]
                                     ↑                          ↓
                               [Axios Client]          [WebSocket Server]
                              (com cookies httpOnly)   (chat em tempo real)
```

O frontend Next.js consome a API de duas formas:
1. **Proxy via Rewrites** (recomendado): O Next.js faz proxy das requisições para o backend, evitando CORS.
2. **Chamadas Diretas**: Configurando `NEXT_PUBLIC_API_URL`, o Axios chama o backend diretamente.

---

## 🛠️ Stack Tecnológica

### Backend (FastAPI)

| Tecnologia        | Versão    | Função                                    |
|-------------------|-----------|-------------------------------------------|
| Python            | 3.11+     | Linguagem de programação                  |
| FastAPI           | 0.136.1   | Framework web assíncrono                  |
| Uvicorn           | 0.47.0    | Servidor ASGI                             |
| SQLAlchemy        | 2.0.25    | ORM assíncrono                            |
| Alembic           | —         | Migrations de banco de dados              |
| Pydantic          | 2.12.5    | Validação de schemas                      |
| PyJWT (python-jose)| 2.12.1   | Tokens JWT                                |
| bcrypt            | 4.0.1     | Hash de senhas                            |
| aiosqlite         | 0.21.0    | Driver SQLite assíncrono                  |
| asyncpg           | 0.29.0    | Driver PostgreSQL assíncrono (opcional)   |
| websockets        | 16.0      | WebSocket para chat em tempo real         |
| CrewAI            | 1.14.4    | Framework de agentes IA (Spottinho)       |
| Google Generative AI | 1.65.0 | Gemini API para o chatbot                |
| Pillow            | 10.2.0    | Otimização de imagens                     |
| sse-starlette     | 3.4.4     | Server-Sent Events                        |

### Frontend (Next.js)

| Tecnologia        | Versão    | Função                                    |
|-------------------|-----------|-------------------------------------------|
| Next.js           | 14.1.0    | Framework React com App Router            |
| React             | 18.2.0    | Biblioteca UI                             |
| TypeScript        | 5.3.3     | Tipagem estática                          |
| Tailwind CSS      | 3.4.1     | Estilização utility-first                 |
| Axios             | 1.15.2    | Cliente HTTP                              |
| Lucide React      | 0.312.0   | Ícones SVG                                |

---

## 🔙 Backend — FastAPI

### Estrutura do Backend

```
backend_fastapi/
├── main.py                   # Entry point da aplicação
├── config.py                 # Configurações (pydantic-settings)
├── database.py               # Engine, Session, Base, get_db()
├── dependencies.py           # JWT, CSRF, get_current_user, get_current_admin
├── utils.py                  # Utilitários (br_time, etc.)
├── requirements.txt          # Dependências Python
│
├── models/                   # Modelos SQLAlchemy (ORM)
│   ├── __init__.py           # Centraliza imports dos modelos
│   ├── user.py               # Usuário
│   ├── post.py               # Post e Comment (feed)
│   ├── notification.py       # Notificações
│   ├── message.py            # Conversa, Mensagem Direta
│   ├── coupon.py             # Cupons de desconto
│   ├── mural.py              # Anúncios do Mural
│   ├── event.py              # Eventos
│   ├── associations.py       # Tabelas associativas (followers, post_likes)
│   ├── audit.py              # Logs de auditoria (admin)
│   └── enums.py              # Enumeradores (EventCategory, etc.)
│
├── schemas/                  # Schemas Pydantic (validação)
│   ├── auth.py               # Login, Registro, AuthResponse
│   ├── post.py               # Post, Comment
│   ├── chat.py               # Mensagens, Conversas
│   ├── event.py              # Eventos
│   ├── mural.py              # Mural
│   ├── notification.py       # Notificações
│   ├── user.py               # Perfil de usuário
│   └── cupons.py             # Cupons
│
├── routes/                   # Rotas da API
│   ├── auth.py               # /auth - registro, login, logout, me
│   ├── feed.py               # /api/feed - CRUD de posts, likes, comentários
│   ├── chat.py               # /api/chat + WebSocket /ws/chat
│   ├── events.py             # /api/events - CRUD de eventos
│   ├── mural.py              # /api/mural - CRUD de anúncios
│   ├── perfil.py             # /api/perfil - Perfil de usuário
│   ├── users.py              # /api/users - Listar/buscar usuários
│   ├── notifications.py      # /api/notifications - Notificações
│   ├── social.py             # /api/social - Follow/Unfollow
│   ├── cupons.py             # /api/cupons - Cupons de desconto
│   ├── upload.py             # /api/upload - Upload de imagens
│   ├── admin.py              # /api/admin - Painel administrativo
│   └── chatbot.py            # /chatbot - Chatbot Spottinho (IA)
│
├── services/                 # Serviços
│   ├── image_service.py      # Otimização e salvamento de imagens
│   ├── password_service.py   # Hash e verificação de senhas (bcrypt)
│   ├── security_service.py   # Sanitização de texto
│   ├── socket_manager.py     # Gerenciador de conexões WebSocket
│   ├── spottinho.py          # Agente IA Spottinho (CrewAI + Gemini)
│   ├── notification_service.py # Serviço de notificações
│   └── startup_service.py    # Serviços de inicialização
│
├── alembic/                  # Migrations
│   ├── versions/             # Versões de migration
│   └── env.py                # Configuração do Alembic
│
├── static/uploads/           # Uploads de imagens
├── instance/                 # Banco SQLite (instance/spotted.db)
└── .env                      # Variáveis de ambiente
```

### Modelos de Dados

Os modelos ORM estão definidos em `backend_fastapi/models/`:

| Modelo              | Tabela           | Descrição                                    |
|---------------------|------------------|----------------------------------------------|
| `User`              | `user`           | Usuários (com autenticação, perfil, admin)   |
| `Post`              | `post`           | Postagens do feed (suporta anonimato)        |
| `Comment`           | `comment`        | Comentários em posts                         |
| `Notification`      | `notification`   | Notificações de interações                   |
| `Conversation`      | `conversation`   | Conversas 1:1                                |
| `ConversationMember`| `conversation_member` | Membros de conversas                   |
| `DirectChatMessage` | `direct_chat_message` | Mensagens diretas                       |
| `Message`           | `message`        | Modelo legado de mensagem                    |
| `MessageReaction`   | `message_reaction` | Reações em mensagens                       |
| `Coupon`            | `coupon`         | Cupons de desconto                           |
| `MuralPost`         | `mural_post`     | Anúncios classificados (mural)               |
| `Event`             | `event`          | Eventos universitários                       |
| `AuditLog`          | `audit_log`      | Logs de ações administrativas                |

**Tabelas Associativas:**
- `followers` — Relacionamento de seguidores (N:N)
- `post_likes` — Curtidas em posts (N:N)

### Rotas / Endpoints

#### Autenticação (`/auth`)

| Método | Rota             | Descrição                            | Autenticação |
|--------|------------------|--------------------------------------|-------------|
| POST   | `/auth/registro` | Registrar novo usuário               | ❌          |
| POST   | `/auth/login`    | Login (suporta JSON e form-data)     | ❌          |
| POST   | `/auth/logout`   | Logout (limpa cookies)               | ❌          |
| GET    | `/auth/me`       | Dados do usuário atual + refresh JWT | ✅ JWT      |

#### Feed (`/api/feed`)

| Método | Rota                              | Descrição                        | Autenticação |
|--------|-----------------------------------|----------------------------------|-------------|
| GET    | `/api/feed/`                      | Listar posts (paginado)          | ❌ (opcional)|
| POST   | `/api/feed/`                      | Criar post (com upload imagens)  | ✅          |
| POST   | `/api/feed/{id}/like`             | Curtir/descurtir post            | ✅          |
| POST   | `/api/feed/{id}/comment`          | Comentar em post                 | ✅          |
| GET    | `/api/feed/{id}/comments`         | Listar comentários               | ❌ (opcional)|
| DELETE | `/api/feed/{id}`                  | Deletar post (autor/admin)       | ✅          |
| DELETE | `/api/feed/comments/{id}`         | Deletar comentário (autor/admin) | ✅          |

#### Chat / Mensagens (`/api/chat`)

| Método | Rota                                   | Descrição                        | Autenticação |
|--------|----------------------------------------|----------------------------------|-------------|
| WS     | `/api/chat/ws`                         | WebSocket para chat em tempo real| ✅ JWT (query/frame)|
| GET    | `/api/chat/conversations`              | Listar conversas do usuário      | ✅          |
| GET    | `/api/chat/history/{user_id}`          | Histórico 1:1 com outro usuário  | ✅          |
| POST   | `/api/chat/send/{user_id}`             | Enviar mensagem via REST (fallback)| ✅        |

#### Eventos (`/api/events`)

| Método | Rota                | Descrição                     | Autenticação |
|--------|---------------------|-------------------------------|-------------|
| GET    | `/api/events/`      | Listar eventos (paginado)     | ❌          |
| GET    | `/api/events/{id}`  | Detalhes de um evento         | ❌          |
| POST   | `/api/events/`      | Criar evento                  | ✅          |
| PATCH  | `/api/events/{id}`  | Atualizar evento (autor/admin)| ✅          |
| DELETE | `/api/events/{id}`  | Deletar evento (autor/admin)  | ✅          |

#### Mural (`/api/mural`)

| Método | Rota                | Descrição                     | Autenticação |
|--------|---------------------|-------------------------------|-------------|
| GET    | `/api/mural/`       | Listar anúncios (paginado)    | ❌          |
| POST   | `/api/mural/`       | Criar anúncio                 | ✅          |
| PUT    | `/api/mural/{id}`   | Atualizar anúncio (autor)     | ✅          |
| DELETE | `/api/mural/{id}`   | Deletar anúncio (autor/admin) | ✅          |

#### Perfil (`/api/perfil`)

| Método | Rota                            | Descrição                     | Autenticação |
|--------|---------------------------------|-------------------------------|-------------|
| GET    | `/api/perfil/{username}`        | Perfil público de um usuário  | ❌ (opcional)|
| PATCH  | `/api/perfil/editar`            | Editar próprio perfil         | ✅          |
| GET    | `/api/perfil/{username}/recados`| Listar recados do mural pessoal| ❌        |
| POST   | `/api/perfil/{username}/recados`| Enviar recado                 | ✅          |

#### Redes Sociais (`/api/social`)

| Método | Rota                       | Descrição                     | Autenticação |
|--------|----------------------------|-------------------------------|-------------|
| POST   | `/api/social/follow/{id}`  | Seguir/deixar de seguir       | ✅          |
| GET    | `/api/social/followers/{id}`| Listar seguidores             | ❌          |
| GET    | `/api/social/following/{id}`| Listar seguindo               | ❌          |

#### Notificações (`/api/notifications`)

| Método | Rota                                  | Descrição                     | Autenticação |
|--------|---------------------------------------|-------------------------------|-------------|
| GET    | `/api/notifications/`                 | Listar notificações           | ✅          |
| POST   | `/api/notifications/{id}/read`        | Marcar como lida              | ✅          |
| POST   | `/api/notifications/read-all`         | Marcar todas como lidas       | ✅          |
| GET    | `/api/notifications/unread-count`     | Contagem de não lidas         | ✅          |

#### Administrativo (`/api/admin`)

| Método | Rota                                    | Descrição                     | Autenticação |
|--------|-----------------------------------------|-------------------------------|-------------|
| GET    | `/api/admin/stats`                      | Estatísticas do dashboard     | ✅ Admin    |
| GET    | `/api/admin/users`                      | Listar todos os usuários      | ✅ Admin    |
| PATCH  | `/api/admin/users/{id}/ban`             | Banir/Desbanir usuário        | ✅ Admin    |
| DELETE | `/api/admin/posts/{id}`                 | Deletar qualquer post         | ✅ Admin    |
| DELETE | `/api/admin/mural/{id}`                 | Deletar qualquer anúncio      | ✅ Admin    |
| DELETE | `/api/admin/coupons/{id}`               | Deletar cupom                 | ✅ Admin    |
| PATCH  | `/api/admin/coupons/{id}/approve`       | Aprovar cupom                 | ✅ Admin    |
| GET    | `/api/admin/logs`                       | Visualizar logs de auditoria  | ✅ Admin    |

#### Chatbot (`/chatbot`)

| Método | Rota                  | Descrição                                 | Autenticação |
|--------|-----------------------|-------------------------------------------|-------------|
| POST   | `/chatbot/perguntar`  | Enviar pergunta para o Spottinho (IA)     | ❌          |

#### Utilitários

| Método | Rota                | Descrição                                |
|--------|---------------------|------------------------------------------|
| GET    | `/`                 | Health check da API                      |
| POST   | `/api/upload`       | Upload de arquivos (imagens)             |
| GET    | `/api/users/search` | Buscar usuários por nome/username        |
| GET    | `/api/users/{id}`   | Dados de um usuário específico           |

### WebSocket

O WebSocket é utilizado para **chat em tempo real** entre usuários.

**Endpoint:** `ws://host:8000/api/chat/ws?token={jwt_token}`

**Fluxo de Conexão:**

1. **Autenticação por query param** (recomendado): O token JWT é enviado como `?token=...`
2. **Fallback**: Se não houver token na query, o servidor aceita a conexão e aguarda um frame JSON com `{"type": "auth", "token": "..."}` (timeout de 10s)
3. Após autenticação, o servidor registra a conexão e permite múltiplas abas/dispositivos

**Tipos de Mensagem:**

| Tipo             | Direção      | Descrição                                    |
|------------------|--------------|----------------------------------------------|
| `ping` / `pong`  | Bidirecional | Heartbeat (cliente envia ping a cada ~25s)   |
| `message`        | Cliente →    | Enviar mensagem para outro usuário           |
| `new_message`    | Servidor →   | Nova mensagem recebida                       |
| `ack`            | Servidor →   | Confirmação de entrega                       |
| `read`           | Cliente →    | Marcar mensagens como lidas                  |
| `read_receipt`   | Servidor →   | Notificação de leitura                       |
| `connected`      | Servidor →   | Confirmação de conexão estabelecida          |

### Autenticação

O sistema utiliza **JWT (JSON Web Tokens)** armazenados em **cookies httpOnly**:

- **Cookie:** `access_token` (httpOnly, Secure em produção, SameSite=Lax)
- **Header alternativo:** `Authorization: Bearer <token>`
- **CSRF Protection:** Cookie `csrf_token` + Header `X-CSRF-Token`
- **Expiração:** Configurável via `JWT_ACCESS_TOKEN_EXPIRE_DAYS` (padrão: 7 dias)
- **Migração de senhas:** Suporta migração automática de hashes legados para bcrypt

### Chatbot Spottinho (IA)

O **Spottinho** é um assistente virtual alimentado por **CrewAI + Google Gemini 2.5 Flash**:

- **Funções:**
  - Tirar dúvidas sobre a plataforma (consulta manual interno)
  - Resumir o feed recente (lê diretamente do banco SQLite)
  - Conversas informais com respostas pré-programadas
- **Endpoint:** `POST /chatbot/perguntar`
- **Respostas rápidas:** Para saudações e perguntas comuns, responde sem acionar a IA

---

## 🎨 Frontend — Next.js

### Estrutura do Frontend

```
frontend/
├── src/
│   ├── app/                      # App Router do Next.js
│   │   ├── globals.css           # Estilos globais
│   │   ├── layout.tsx            # Layout raiz (AuthProvider + WebsocketProvider)
│   │   ├── (auth)/               # Grupo de rotas públicas
│   │   │   ├── layout.tsx        # Layout de autenticação
│   │   │   ├── login/page.tsx    # Página de login
│   │   │   └── registro/page.tsx # Página de cadastro
│   │   └── (app)/                # Grupo de rotas protegidas
│   │       ├── layout.tsx        # Layout principal (Sidebar, Navbar, AuthGuard)
│   │       ├── page.tsx          # Home → redireciona para /feed
│   │       ├── feed/page.tsx     # Feed principal
│   │       ├── explorar/page.tsx # Página explorar
│   │       ├── eventos/page.tsx  # Eventos
│   │       ├── mural/page.tsx    # Mural de anúncios
│   │       ├── notificacoes/page.tsx  # Notificações
│   │       ├── perfil/[username]/page.tsx  # Perfil do usuário
│   │       ├── perfil/editar/page.tsx      # Editar perfil
│   │       ├── direct/page.tsx   # Direct Messages (lista conversas)
│   │       ├── dm/[userId]/page.tsx  # Chat com usuário específico
│   │       ├── admin/page.tsx    # Painel administrativo
│   │       └── suporte/page.tsx  # Suporte / Spottinho
│   │
│   ├── components/               # Componentes reutilizáveis
│   │   ├── Sidebar.tsx           # Sidebar lateral esquerda (desktop)
│   │   ├── MobileSidebar.tsx     # Sidebar móvel (overlay)
│   │   ├── MobileNavbar.tsx      # Navbar inferior (mobile)
│   │   ├── Navbar.tsx            # Navbar superior
│   │   ├── RightSidebar.tsx      # Sidebar direita (desktop)
│   │   ├── Feed.tsx              # Componente de feed
│   │   ├── FeedList.tsx          # Lista de posts
│   │   ├── PostCard.tsx          # Card de post individual
│   │   ├── PostCarousel.tsx      # Carrossel de imagens do post
│   │   ├── SearchBar.tsx         # Barra de busca
│   │   ├── CreatePost.tsx        # Criar post (botão FAB)
│   │   ├── CreatePostModal.tsx   # Modal de criação de post
│   │   ├── CreateEventModal.tsx  # Modal de criação de evento
│   │   ├── CreateMuralModal.tsx  # Modal de criação de anúncio
│   │   ├── EditProfileModal.tsx  # Modal de edição de perfil
│   │   ├── ProfileHeader.tsx     # Header do perfil
│   │   ├── ProfileSidebarModal.tsx # Sidebar do perfil
│   │   ├── Chat.tsx              # Componente de chat
│   │   ├── ConversationList.tsx  # Lista de conversas
│   │   ├── EventFAB.tsx          # FAB de eventos
│   │   ├── FeedFAB.tsx           # FAB do feed
│   │   ├── MuralFAB.tsx          # FAB do mural
│   │   ├── FloatingButton.tsx    # Botão flutuante geral
│   │   ├── EventosWidget.tsx     # Widget de eventos
│   │   ├── MuralWidget.tsx       # Widget do mural
│   │   ├── NotificationBell.tsx   # Sino de notificações
│   │   ├── SpottinhoCard.tsx     # Card do Spottinho (assistente)
│   │   └── TabSwitcher.tsx       # Alternador de abas
│   │
│   ├── context/                  # Contextos React
│   │   ├── AuthContext.tsx       # Autenticação global
│   │   ├── PostContext.tsx       # Estado dos posts
│   │   └── WebsocketContext.tsx  # Conexão WebSocket
│   │
│   ├── hooks/                    # Hooks personalizados
│   │   ├── useChat.ts            # Hook de chat WebSocket
│   │   ├── useFeed.ts            # Hook de feed
│   │   └── useScrollDirection.ts # Hook de direção de scroll
│   │
│   ├── lib/                      # Utilitários
│   │   ├── api-base.ts           # Resolução de URLs (API, Socket, Upload)
│   │   ├── api-client.ts         # Instância Axios com interceptors
│   │   ├── api.ts                # Funções auxiliares da API
│   │   └── auth-token.ts         # Gerenciamento de token (sessionStorage)
│   │
│   ├── types/
│   │   └── index.ts              # Interfaces TypeScript (User, Post, Chat, etc.)
│   │
│   └── middleware.ts             # Middleware Edge (Next.js) para proteção de rotas
│
├── public/                       # Arquivos estáticos públicos
├── static/uploads/               # Uploads servidos estaticamente
├── .env                          # Variáveis de ambiente
├── .gitignore                    # Git ignore do frontend
├── next.config.js                # Configuração do Next.js
├── tailwind.config.ts            # Configuração do Tailwind
├── tsconfig.json                 # Configuração do TypeScript
└── package.json                  # Dependências do projeto
```

### Componentes

#### Layout Principal (`(app)/layout.tsx`)
- **AuthGuard:** Componente que verifica autenticação client-side antes de renderizar
- **Grid de 3 colunas:** Sidebar | Conteúdo | RightSidebar
- **Navbar:** Cabeçalho com navegação
- **MobileSidebar:** Menu lateral para dispositivos móveis
- **FloatingButton:** Botão de ação flutuante (mobile)

#### Páginas

| Rota              | Descrição                                    |
|-------------------|----------------------------------------------|
| `/`               | Redireciona para `/feed`                     |
| `/login`          | Tela de login com formulário estilizado      |
| `/registro`       | Tela de cadastro de novo usuário             |
| `/feed`           | Feed principal com timeline infinita         |
| `/explorar`       | Grade de descoberta de conteúdo              |
| `/eventos`        | Lista de eventos universitários              |
| `/mural`          | Mural de classificados/anúncios              |
| `/perfil/[user]`  | Perfil público do usuário                    |
| `/perfil/editar`  | Edição do próprio perfil                     |
| `/direct`         | Lista de conversas de Direct Messages        |
| `/dm/[userId]`    | Chat 1:1 com WebSocket em tempo real         |
| `/notificacoes`   | Central de notificações                      |
| `/admin`          | Painel administrativo                        |
| `/suporte`        | Assistente Spottinho (chatbot)               |

### Contextos (Estado Global)

| Contexto             | Função                                                    |
|----------------------|-----------------------------------------------------------|
| `AuthContext`        | Estado do usuário logado, token, login/logout/refresh     |
| `PostContext`        | Gerenciamento de posts no feed (add post, filtrar)        |
| `WebsocketContext`   | Provedor de conexão WebSocket (estrutura inicial)         |

### Hooks Personalizados

| Hook                    | Descrição                                                    |
|-------------------------|--------------------------------------------------------------|
| `useChat`               | Conexão WebSocket para chat em tempo real com auto-reconnect |
| `useFeed`               | Carregamento de posts do feed com paginação                  |
| `useScrollDirection`    | Detecta direção do scroll (para esconder/mostrar elementos)  |

### Middleware de Autenticação

O arquivo `src/middleware.ts` é um **Edge Middleware** do Next.js que:

1. **Bloqueia rotas protegidas** sem token → redireciona para `/login`
2. **Redireciona usuários logados** de `/login` ou `/registro` para `/feed`
3. **Verifica cookies:** `access_token`, `token`, `jwt`
4. **Configuração de rotas monitoradas** via `matcher`

### Estilização

- **Tema escuro** (`!bg-black !text-zinc-100`)
- **Paleta roxa (violet)** como cor principal do Spotted Social
- **Tailwind CSS** com configuração personalizada
- **Animações:** `glow-pulse` para efeitos de brilho

---

## 🚀 Como Executar o Projeto

### Pré-requisitos

- **Python 3.11+**
- **Node.js 18+**
- **npm** ou **yarn**
- **Git**

### Backend

```bash
# 1. Acesse a pasta do backend
cd backend_fastapi

# 2. Crie um ambiente virtual
python -m venv venv

# 3. Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Configure as variáveis de ambiente
# Edite o arquivo .env com suas configurações
# ⚠️ Gere uma SECRET_KEY forte:
#    python -c "import secrets; print(secrets.token_hex(32))"

# 6. Execute as migrations
alembic upgrade head

# 7. Inicie o servidor
python main.py
# O servidor iniciará em http://localhost:8000
# Documentação interativa: http://localhost:8000/docs
```

### Frontend

```bash
# 1. Acesse a pasta do frontend
cd frontend

# 2. Instale as dependências
npm install
# ou
yarn install

# 3. Configure o arquivo .env
# Defina NEXT_PUBLIC_API_URL se quiser chamadas diretas
# Deixe vazio para usar o proxy do Next.js

# 4. Inicie o servidor de desenvolvimento
npm run dev
# O servidor iniciará em http://localhost:3000

# 5. Para build de produção
npm run build
npm run start
```

---

## 🔐 Variáveis de Ambiente

### Backend (`backend_fastapi/.env`)

| Variável                    | Descrição                                      | Padrão                    |
|-----------------------------|------------------------------------------------|---------------------------|
| `SECRET_KEY`                | Chave secreta para JWT (obrigatório!)          | `change-me-in-production` |
| `DATABASE_URL`              | URL de conexão com o banco                     | `sqlite+aiosqlite:///./instance/spotted.db` |
| `CORS_ORIGINS`              | Origens permitidas para CORS                   | `http://localhost:3000,...` |
| `JWT_COOKIE_SECURE`         | Cookie Secure (true em produção)               | `false` (dev) / `true` (prod) |
| `JWT_COOKIE_SAMESITE`       | SameSite do cookie JWT                         | `Lax`                     |
| `SESSION_EXPIRE_DAYS`       | Dias de expiração do token                     | `7`                       |
| `UPLOAD_FOLDER`             | Pasta de uploads                               | `static/uploads`          |
| `MAX_CONTENT_LENGTH`        | Tamanho máximo de upload (bytes)               | `31457280` (30MB)         |
| `FEED_PAGE_SIZE`            | Posts por página no feed                       | `8`                       |
| `SPOTTED_ENV`               | Perfil de execução (`dev` ou `prod`)           | `dev`                     |
| `ADMIN_SEED_ENABLED`        | Criar admin automaticamente no startup         | `false`                   |
| `ADMIN_USERNAME`            | Username do admin seed                         | `admin`                   |
| `ADMIN_PASSWORD`            | Senha do admin seed                            | —                         |

### Frontend (`frontend/.env`)

| Variável                  | Descrição                                              | Padrão              |
|---------------------------|--------------------------------------------------------|---------------------|
| `NEXT_PUBLIC_API_URL`     | URL da API (deixe vazio para usar proxy do Next.js)    | —                   |
| `NEXT_PUBLIC_SOCKET_URL`  | URL do WebSocket (deixe vazio para usar proxy)         | —                   |
| `NEXT_PUBLIC_URL`         | URL pública do frontend (para meta tags OG)            | `http://localhost:3000` |

---

## 🌐 Deploy

### Backend (Produção)

Para ambiente de produção, recomenda-se:

1. **Banco de dados:** migrar de SQLite para PostgreSQL
2. **Servidor:** usar Gunicorn + Uvicorn workers
3. **Proxy reverso:** Nginx ou Caddy na frente do FastAPI
4. **SSL:** Certificado HTTPS (Let's Encrypt)
5. **CORS:** Configurar `CORS_ORIGINS` com o domínio do frontend

```bash
# Exemplo de execução em produção
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend (Produção)

1. **Build:** `npm run build`
2. **Deploy:** Vercel, Netlify, ou servidor próprio com Node.js
3. **Variáveis de ambiente:** Configurar `NEXT_PUBLIC_API_URL` apontando para o backend (ou usar proxy)

---

## ✨ Funcionalidades

- ✅ **Feed Global** — Timeline com posts em ordem cronológica, suporte a múltiplas imagens
- ✅ **Anonimato** — Posts podem ser publicados anonimamente (anonimato garantido)
- ✅ **Curtidas e Comentários** — Interaja com posts de outros usuários
- ✅ **Direct Messages** — Chat em tempo real via WebSocket com suporte a múltiplas abas
- ✅ **Notificações** — Receba notificações de curtidas, comentários e mensagens
- ✅ **Seguir Usuários** — Siga outros usuários e veja seus posts
- ✅ **Perfil Personalizável** — Bio, foto, link social, universidade
- ✅ **Mural de Anúncios** — Classificados universitários por categoria
- ✅ **Eventos** — Criação e gerenciamento de eventos universitários
- ✅ **Explorar** — Descubra novos conteúdos
- ✅ **Spottinho (IA)** — Assistente virtual com inteligência artificial (CrewAI + Gemini)
- ✅ **Painel Admin** — Dashboard com estatísticas, moderação de conteúdo, banimento de usuários
- ✅ **Auditoria** — Log de todas as ações administrativas
- ✅ **Cupons** — Sistema de cupons de desconto
- ✅ **CSRF Protection** — Proteção contra Cross-Site Request Forgery
- ✅ **Responsivo** — Design adaptável para desktop e mobile
- ✅ **Tema Escuro** — Interface dark mode

---

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie sua branch de feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto é de uso privado. Todos os direitos reservados.

---

<p align="center">
  <strong>Spotted Social</strong> — Compartilhe segredos e momentos da sua universidade com total liberdade.
</p>
