"""Direct Messages – WebSocket + REST API.

Provides:
  • WebSocket /ws/chat – real-time messaging with JWT validation
  • GET  /api/chat/conversations          – lista conversas do usuário
  • GET  /api/chat/history/{other_user_id} – histórico 1:1
  • POST /api/chat/send/{user_id}         – enviar via REST (fallback)

Database persistence:
  • Uses the existing DirectChatMessage model
  • Creates/finds a Conversation (1:1) on first message
  • Messages saved to DB *before* WebSocket delivery
  • Read receipts are sent via WebSocket
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import settings # No change here
from database import get_db # No change here
from dependencies import decode_access_token, get_current_user, get_optional_user # No change here
from models import Conversation, ConversationMember, DirectChatMessage, Notification, User # Import from models/__init__.py
from utils import br_time # Centralized import

from schemas.chat import (
    ChatHistoryResponse,
    ConversationListResponse,
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from services.socket_manager import manager
from services.security_service import sanitize_user_text

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚══════════════════════════════════════════════════════════════════════╝

async def _get_or_create_1on1_conversation(
    db: AsyncSession,
    user_a_id: int,
    user_b_id: int,
) -> Conversation:
    """Find or create a 1:1 conversation between two users."""
    # Look for existing conversation where both are members
    # We check if there's a conversation with exactly those two members
    subq = (
        select(ConversationMember.conversation_id)
        .where(ConversationMember.user_id.in_([user_a_id, user_b_id]))
        .group_by(ConversationMember.conversation_id)
        .having(func.count(ConversationMember.id) == 2)
    ).subquery()

    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.members), selectinload(Conversation.messages))
        .where(Conversation.id.in_(select(subq)))
        .where(Conversation.is_group.is_(False))
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Create new conversation
    slug = f"1on1_{min(user_a_id, user_b_id)}_{max(user_a_id, user_b_id)}"
    conv = Conversation(
        slug=slug,
        is_group=False,
        created_at=br_time(),
    )
    db.add(conv)
    await db.flush()

    # Add both members
    for uid in (user_a_id, user_b_id):
        member = ConversationMember(
            conversation_id=conv.id,
            user_id=uid,
        )
        db.add(member)
    await db.flush()

    return conv


async def _save_message(
    db: AsyncSession,
    conversation_id: int,
    sender_id: int,
    content: str,
    media_url: Optional[str] = None,
) -> DirectChatMessage:
    """Persist a message and return it."""
    msg = DirectChatMessage(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        media_url=media_url,
        created_at=br_time(),
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


def _serialize_message(msg: DirectChatMessage) -> dict[str, Any]:
    """Convert a DirectChatMessage to a JSON-safe dict."""
    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "media_url": msg.media_url,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "all_read": msg.all_read,
    }


async def _get_other_user_id(
    conversation: Conversation,
    current_user_id: int,
) -> Optional[int]:
    """Return the other user's ID in a 1:1 conversation."""
    for member in conversation.members:
        if member.user_id != current_user_id:
            return member.user_id
    return None


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  WEBSOCKET /ws/chat                                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat (secure).

    Auth flow:
      1. Try to extract JWT from ?token= query parameter
      2. If not in query, accept connection and wait for first frame
         containing {"type": "auth", "token": "..."}
      3. Validate JWT; if invalid, close with code 4008
      4. On success, register connection and start message loop
    """
    user_id = None

    # -- 1. Try query param first (validate BEFORE accept) --
    token = websocket.query_params.get("token")
    payload = None

    if token:
        try:
            payload = decode_access_token(token)
        except Exception:
            pass

    if payload is not None:
        user_id = payload.get("sub")

    if user_id is not None:
        # Valid token via query param -> accept straight away
        await manager.connect(user_id, websocket)
        logger.info("WS chat: user=%d connected (via query token)", user_id)
        await manager.send_personal_message(user_id, {
            "type": "connected",
            "user_id": user_id,
        })
    else:
        # -- 2. No valid token in query -> accept, wait for auth frame --
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        except asyncio.TimeoutError:
            await websocket.close(code=4008, reason="Autenticacao nao recebida.")
            return

        try:
            auth_data = json.loads(raw)
        except json.JSONDecodeError:
            await websocket.close(code=4008, reason="Formato invalido.")
            return

        if auth_data.get("type") != "auth" or not auth_data.get("token"):
            await websocket.close(code=4008, reason="Token nao fornecido.")
            return

        try:
            payload = decode_access_token(auth_data["token"])
            user_id = payload.get("sub")
            if user_id is None:
                await websocket.close(code=4008, reason="Token invalido.")
                return
        except Exception:
            await websocket.close(code=4008, reason="Token invalido ou expirado.")
            return

        # Register (websocket already accepted)
        async with manager._lock:
            if user_id not in manager._connections:
                manager._connections[user_id] = []
            manager._connections[user_id].append(websocket)

        logger.info("WS chat: user=%d connected (via auth frame)", user_id)
        await websocket.send_text(json.dumps({
            "type": "connected",
            "user_id": user_id,
        }))

    # -- 3. Message loop --
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "JSON invalido.",
                }))
                continue

            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "message":
                await _handle_ws_message(user_id, data, websocket)

            elif msg_type == "read":
                await _handle_ws_read(user_id, data)

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": f"Tipo desconhecido: {msg_type}",
                }))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WS error user=%d: %s", user_id, exc, exc_info=True)
    finally:
        await manager.disconnect(user_id, websocket)
        logger.info("WS chat: user=%d disconnected", user_id)


async def _handle_ws_message(
    sender_id: int,
    data: dict[str, Any],
    websocket: WebSocket,
) -> None:
    """Handle an incoming chat message via WebSocket."""
    from database import async_session_factory

    to_user_id = data.get("to")
    content = data.get("content", "").strip()

    if not to_user_id or not content:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Campos 'to' e 'content' são obrigatórios.",
        }))
        return

    if not isinstance(to_user_id, int) or to_user_id == sender_id:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Destinatário inválido.",
        }))
        return

    if len(content) > 500:
        content = content[:500]

    # Sanitize
    content = sanitize_user_text(content, max_len=500)

    # Persist in DB
    async with async_session_factory() as db:
        try:
            conv = await _get_or_create_1on1_conversation(db, sender_id, to_user_id)
            msg = await _save_message(db, conv.id, sender_id, content)

            # Create notification for recipient
            try:
                # Get sender name
                sender_result = await db.execute(select(User).where(User.id == sender_id))
                sender = sender_result.scalar_one_or_none()
                sender_name = sender.name or sender.username if sender else "Alguém"

                notif = Notification(
                    user_id=to_user_id,
                    sender_name=sender_name,
                    action_type="enviou uma mensagem",
                    category="dm",
                )
                db.add(notif)
            except Exception:
                pass

            await db.commit()
            await db.refresh(msg)

            serialized = _serialize_message(msg)
            serialized["sender_name"] = sender_name if 'sender_name' in locals() else None

        except Exception as exc:
            await websocket.send_text(json.dumps({
                "type": "error",
                "detail": f"Erro ao salvar mensagem: {str(exc)}",
            }))
            return

    # Send ack to sender
    await websocket.send_text(json.dumps({
        "type": "ack",
        "message_id": msg.id,
        "conversation_id": conv.id,
    }))

    # Deliver to recipient if online
    sent_count = await manager.send_personal_message(to_user_id, {
        "type": "new_message",
        "conversation_id": conv.id,
        "message": serialized,
    })

    # If offline, message is already saved and will appear on history fetch


async def _handle_ws_read(
    user_id: int,
    data: dict[str, Any],
) -> None:
    """Handle read receipt via WebSocket."""
    from database import async_session_factory

    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return

    async with async_session_factory() as db:
        try:
            # Mark messages as read (sent to this user)
            result = await db.execute(
                select(DirectChatMessage)
                .where(
                    DirectChatMessage.conversation_id == conversation_id,
                    DirectChatMessage.sender_id != user_id,
                    DirectChatMessage.all_read.is_(False),
                )
            )
            unread = result.scalars().all()
            for msg in unread:
                msg.all_read = True
            await db.commit()

            # Notify the other user that messages were read
            # Find the other user in this conversation
            other_result = await db.execute(
                select(ConversationMember)
                .where(
                    ConversationMember.conversation_id == conversation_id,
                    ConversationMember.user_id != user_id,
                )
                .limit(1)
            )
            other_member = other_result.scalar_one_or_none()
            if other_member:
                await manager.send_personal_message(
                    other_member.user_id,
                    {
                        "type": "read_receipt",
                        "conversation_id": conversation_id,
                        "read_by": user_id,
                        "message_ids": [m.id for m in unread],
                    },
                )
        except Exception as exc:
            logger.error("Read receipt error: %s", exc)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/chat/conversations – Listar conversas                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas as conversas do usuário logado, com a última mensagem."""
    # Find conversations where user is a member
    result = await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.members).selectinload(ConversationMember.user),
            selectinload(Conversation.messages),
        )
        .where(
            Conversation.id.in_(
                select(ConversationMember.conversation_id)
                .where(ConversationMember.user_id == current_user.id)
            )
        )
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()

    items = []
    for conv in conversations:
        # Find the other user
        other_user = None
        for member in conv.members:
            if member.user_id != current_user.id and member.user:
                other_user = member.user
                break

        # Get last message
        last_msg = None
        if conv.messages:
            conv.messages.sort(key=lambda m: m.created_at or datetime.min, reverse=True)
            last_msg = conv.messages[0]

        items.append({
            "conversation_id": conv.id,
            "other_user_id": other_user.id if other_user else None,
            "other_username": other_user.username if other_user else None,
            "other_name": other_user.name if other_user else None,
            "other_profile_pic": other_user.profile_pic if other_user else None,
            "last_message": last_msg.content if last_msg else None,
            "last_message_at": last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None,
            "unread_count": sum(
                1 for m in conv.messages
                if m.sender_id != current_user.id and not m.all_read
            ),
            "is_online": manager.is_online(other_user.id) if other_user else False,
        })

    return ConversationListResponse(items=items)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/chat/history/{other_user_id} – Histórico 1:1              ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/history/{other_user_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    other_user_id: int,
    limit: int = Query(50, ge=1, le=200, description="Quantidade de mensagens"),
    before_msg_id: Optional[int] = Query(None, description="Cursor: pegar mensagens anteriores a este ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna o histórico de mensagens entre o usuário logado e outro.

    As mensagens NÃO LIDAS enviadas pelo *outro* usuário são marcadas
    como lidas automaticamente, e uma notificação de leitura é enviada
    via WebSocket se o remetente estiver online.
    """
    if other_user_id == current_user.id:
        raise HTTPException(status_code=422, detail="Você não pode conversar consigo mesmo.")

    # Find the 1:1 conversation
    conv = await _get_or_create_1on1_conversation(db, current_user.id, other_user_id)

    # Build query
    query = (
        select(DirectChatMessage)
        .where(DirectChatMessage.conversation_id == conv.id)
        .order_by(DirectChatMessage.created_at.desc(), DirectChatMessage.id.desc())
    )

    if before_msg_id:
        query = query.where(DirectChatMessage.id < before_msg_id)

    result = await db.execute(query.limit(limit))
    messages_raw = result.scalars().all()
    messages_raw.reverse()  # oldest first

    # Mark unread messages as read (sent by other user)
    unread_ids = []
    for msg in messages_raw:
        if msg.sender_id == other_user_id and not msg.all_read:
            msg.all_read = True
            unread_ids.append(msg.id)
    if unread_ids:
        await db.flush()
        # Notify sender via WebSocket
        await manager.send_personal_message(
            other_user_id,
            {
                "type": "read_receipt",
                "conversation_id": conv.id,
                "read_by": current_user.id,
                "message_ids": unread_ids,
            },
        )

    # Serialize
    messages = []
    for msg in messages_raw:
        msg_dict = _serialize_message(msg)
        # Add sender info
        if msg.sender_id == current_user.id:
            msg_dict["is_mine"] = True
        else:
            msg_dict["is_mine"] = False
        messages.append(msg_dict)

    # Get other user info
    other_result = await db.execute(select(User).where(User.id == other_user_id))
    other_user = other_result.scalar_one_or_none()

    return ChatHistoryResponse(
        conversation_id=conv.id,
        other_user_id=other_user_id,
        other_username=other_user.username if other_user else None,
        other_name=other_user.name if other_user else None,
        other_profile_pic=other_user.profile_pic if other_user else None,
        messages=messages,
        is_online=manager.is_online(other_user_id),
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  POST /api/chat/send/{user_id} – Enviar via REST (fallback)          ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.post("/send/{user_id}", response_model=SendMessageResponse)
async def send_message_rest(
    user_id: int,
    payload: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envia uma mensagem via REST (fallback quando WebSocket não disponível).

    Se o destinatário estiver online, a mensagem será entregue em tempo real
    via WebSocket.
    """
    if user_id == current_user.id:
        raise HTTPException(status_code=422, detail="Você não pode enviar mensagem para si mesmo.")

    # Verify recipient exists
    recipient_result = await db.execute(select(User).where(User.id == user_id))
    recipient = recipient_result.scalar_one_or_none()
    if not recipient:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    content = sanitize_user_text(payload.content, max_len=500)
    if not content:
        raise HTTPException(status_code=422, detail="A mensagem não pode estar vazia.")

    # Save to DB
    conv = await _get_or_create_1on1_conversation(db, current_user.id, user_id)
    msg = await _save_message(db, conv.id, current_user.id, content)

    # Notification
    try:
        notif = Notification(
            user_id=user_id,
            sender_name=current_user.name or current_user.username,
            action_type="enviou uma mensagem",
            category="dm",
        )
        db.add(notif)
    except Exception:
        pass

    await db.commit()
    await db.refresh(msg)

    serialized = _serialize_message(msg)
    serialized["is_mine"] = False

    # Try real-time delivery
    sent_count = await manager.send_personal_message(user_id, {
        "type": "new_message",
        "conversation_id": conv.id,
        "message": serialized,
    })

    return SendMessageResponse(
        ok=True,
        message_id=msg.id,
        conversation_id=conv.id,
        delivered_online=sent_count > 0,
    )
