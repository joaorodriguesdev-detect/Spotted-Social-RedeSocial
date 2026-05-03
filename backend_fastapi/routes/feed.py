"""Feed Global – FastAPI APIRouter.

Provides:
  • GET /api/feed – feed combinado: posts de seguidos + posts globais
  • POST /api/feed – criar novo post
  • POST /api/feed/{post_id}/like – like/unlike
  • POST /api/feed/{post_id}/comment – comentar
  • DELETE /api/feed/{post_id} – excluir

Migrated from routes/feed.py with:
  • async def
  • Pydantic schemas (PostResponse)
  • Offset/limit pagination (em vez de cursor)
  • Feed híbrido: seguidos primeiro, depois globais
  • Dados do autor embutidos (sem chamadas extras)
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db # Assuming get_db is in database.py
from dependencies import get_current_user, get_optional_user # Assuming these are in dependencies.py
from models import Comment, Post, post_likes, Notification, User, followers # Import from models/__init__.py
from utils import br_time # Centralized import

from schemas.post import CommentCreate, CommentResponse, PostCreate, PostResponse
from services.image_service import save_and_optimize_image
from services.security_service import sanitize_user_text

router = APIRouter(prefix="/api/feed", tags=["feed"])


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  HELPERS                                                             ║
# ╚══════════════════════════════════════════════════════════════════════╝

async def _build_post_response(
    post: Post,
    db: AsyncSession,
    current_user_id: Optional[int] = None,
) -> PostResponse:
    """Convert a Post ORM object into a PostResponse.

    Já inclui todos os dados do autor para evitar N+1 queries.
    """
    liked_by_me = False
    if current_user_id is not None:
        result = await db.execute(
            select(post_likes).where(
                post_likes.c.user_id == current_user_id,
                post_likes.c.post_id == post.id,
            )
        )
        liked_by_me = result.first() is not None

        author_username = None
    author_name = None
    author_profile_pic = None
    comment_count = len(post.comments) if post.comments else 0
    if post.author:
        author_username = post.author.username if not post.is_anonymous else "Anônimo"
        author_name = post.author.name if not post.is_anonymous else "Anônimo"
        author_profile_pic = post.author.profile_pic if not post.is_anonymous else None

    return PostResponse(
        id=post.id,
        content=post.content,
        media_url=post.media_url,
        media_urls=post.media_urls or [],
        timestamp=post.timestamp,
        likes=post.likes,
        user_id=post.user_id,
        is_anonymous=post.is_anonymous,
        liked_by_me=liked_by_me,
        author_username=author_username,
        author_name=author_name,
        author_profile_pic=author_profile_pic,
        comment_count=comment_count,
    )


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/feed – Feed combinado (paginado com offset/limit)          ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/", response_model=dict)
async def get_feed(
    page: int = Query(1, ge=1, description="Número da página (inicia em 1)"),
    limit: int = Query(10, ge=1, le=50, description="Posts por página"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Retorna o feed combinado: posts de quem o usuário segue + posts globais.

    Regras:
      • Usuário logado: primeiros os posts de quem ele segue, depois globais.
      • Usuário não logado: apenas posts globais (todos).
      • Paginação via offset/limit (simples para o frontend).
      • Cada post já vem com dados completos do autor.
    """
    current_user_id = current_user.id if current_user else None
    offset = (page - 1) * limit

    # ── Sub-query: IDs dos usuários seguidos (se logado) ──────────────
    followed_ids: List[int] = []
    if current_user:
        # Recupera os IDs de quem o usuário segue
        followed_result = await db.execute(
            select(followers.c.followed_id).where(
                followers.c.follower_id == current_user.id
            )
        )
        followed_ids = [row[0] for row in followed_result.all()]

    # ── Query base com eager loading do autor e comentários ────────────
    base_query = (
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments))
    )

    if followed_ids:
        # Feed híbrido: posts de seguidos + posts de não-seguidos
        # Usamos uma UNION ordenada: seguidos primeiro, depois globais
        followed_posts = (
                        base_query.where(Post.user_id.in_(followed_ids)).order_by(
                Post.timestamp.desc(), Post.id.desc()
            )
        )
        global_posts = (
            base_query
            .where(
                or_(~Post.user_id.in_(followed_ids), Post.user_id.is_(None))
            )
            .order_by(Post.timestamp.desc(), Post.id.desc())
        )

        # Aplica offset/limit na primeira parte (seguidos)
        followed_result = await db.execute(
            followed_posts.offset(offset).limit(limit)
        )
        followed_posts_list = followed_result.scalars().all()

        if len(followed_posts_list) < limit:
            # Se não preencheu a página, busca posts globais para completar
            remaining = limit - len(followed_posts_list)
            global_result = await db.execute(
                global_posts.offset(0).limit(remaining)
            )
            global_posts_list = global_result.scalars().all()
            posts = followed_posts_list + global_posts_list
            has_more = len(global_posts_list) == remaining and (
                await db.execute(global_posts.offset(remaining).limit(1))
            ).scalar_one_or_none() is not None
        else:
            # Já preencheu a página só com seguidos
            posts = followed_posts_list
            # Verifica se há mais posts de seguidos
            has_more = (
                await db.execute(followed_posts.offset(offset + limit).limit(1))
            ).scalar_one_or_none() is not None

        # Se não há mais posts de seguidos, nem globais
        if not posts:
            has_more = False
    else:
        # Usuário não logado ou não segue ninguém → feed global
        query = base_query.order_by(Post.timestamp.desc(), Post.id.desc())
        result = await db.execute(query.offset(offset).limit(limit + 1))
        rows = result.scalars().all()
        has_more = len(rows) > limit
        posts = rows[:limit]

    # ── Monta resposta ────────────────────────────────────────────────
    items = []
    for post in posts:
        item = await _build_post_response(post, db, current_user_id)
        items.append(item.model_dump())

    total_count = len(items)

    return {
        "items": items,
        "has_more": has_more,
        "page": page,
        "limit": limit,
        "total_count": total_count,
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  POST /api/feed – Create a new post                                  ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    # Accept both JSON body OR form data (for file upload)
    content: str = Form(..., min_length=1, max_length=5000),
    is_anonymous: bool = Form(False),
    files: List[UploadFile] = File(default=[], description="Imagens opcionais (máx 2)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new post in the feed.

    Accepts multipart/form-data so you can optionally upload up to 2 images
    along with the text content.
    """
    if len(files) > 2:
        raise HTTPException(status_code=400, detail="Máximo de 2 imagens permitidas.")

    # Sanitize content
    clean_content = sanitize_user_text(content, max_len=5000)

    # Handle image upload
    media_url = None
    media_urls = []
    for file in files:
        if file and file.filename:
            filename_base = str(uuid.uuid4())
            # Save the uploaded file
            url = await save_and_optimize_image(
                file,
                filename_base,
                upload_folder="static/uploads",
            )
            if url:
                media_urls.append(url)
    
    if media_urls:
        media_url = media_urls[0]

    post = Post(
        content=clean_content,
        media_url=media_url,
        media_urls=media_urls,
        user_id=current_user.id,
        is_anonymous=is_anonymous,
                timestamp=br_time(),
    )
    db.add(post)
    await db.flush()
    await db.commit()
    await db.refresh(post)

    # Reload with relationships
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.comments))
        .where(Post.id == post.id)
    )
    post = result.scalar_one()

    return await _build_post_response(post, db, current_user.id)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  POST /api/feed/{post_id}/like – Toggle like                         ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.post("/{post_id}/like", response_model=dict)
async def toggle_like(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle the like status on a post. Returns the new like count and state."""
    result = await db.execute(
        select(Post).options(selectinload(Post.liked_by)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado.")

    # Check if already liked
    liked_result = await db.execute(
        select(post_likes).where(
            post_likes.c.user_id == current_user.id,
            post_likes.c.post_id == post_id,
        )
    )
    already_liked = liked_result.first() is not None

    if already_liked:
        # Unlike
        await db.execute(
            post_likes.delete().where(
                post_likes.c.user_id == current_user.id,
                post_likes.c.post_id == post_id,
            )
        )
        post.likes = max(0, post.likes - 1)
        liked = False
    else:
        # Like
        await db.execute(
            post_likes.insert().values(
                user_id=current_user.id,
                post_id=post_id,
            )
        )
        post.likes = (post.likes or 0) + 1
        liked = True

                # Notify post author (if not self-like)
        if post.user_id and post.user_id != current_user.id:
            notif = Notification(
                user_id=post.user_id,
                sender_name=current_user.name or current_user.username,
                action_type="curtiu sua publicação",
                post_id=post.id,
            )
            db.add(notif)

    await db.commit()

    return {
        "ok": True,
        "liked": liked,
        "likes": post.likes,
    }


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  POST /api/feed/{post_id}/comment – Add comment                      ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.post("/{post_id}/comment", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: int,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a comment to a post."""
    # Verify post exists
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado.")

    content = sanitize_user_text(payload.content, max_len=500)
    if not content:
        raise HTTPException(status_code=422, detail="O comentário não pode estar vazio.")

    comment = Comment(
        post_id=post_id,
        content=content,
        user_id=current_user.id,
                timestamp=br_time(),
    )
    db.add(comment)
    # comments_count is derived from len(post.comments) at response time

        # Notify post author
    if post.user_id and post.user_id != current_user.id:
        notif = Notification(
            user_id=post.user_id,
            sender_name=current_user.name or current_user.username,
            action_type="comentou sua publicação",
            post_id=post.id,
        )
        db.add(notif)

    await db.commit()
    await db.refresh(comment)

    return CommentResponse.model_validate(comment)


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  GET /api/feed/{post_id}/comments – List comments                    ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.get("/{post_id}/comments", response_model=List[CommentResponse])
async def list_comments(
    post_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List comments for a post."""
    result = await db.execute(
        select(Comment)
        .where(Comment.post_id == post_id)
        .order_by(Comment.timestamp.asc())
        .offset(skip)
        .limit(limit)
    )
    comments = result.scalars().all()
    return [CommentResponse.model_validate(c) for c in comments]


# ╔══════════════════════════════════════════════════════════════════════╗
# ║  DELETE /api/feed/{post_id} – Delete a post                          ║
# ╚══════════════════════════════════════════════════════════════════════╝

@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a post (author or admin only)."""
    result = await db.execute(
        select(Post).options(selectinload(Post.comments)).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post não encontrado.")

    if post.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissão para deletar.")

    # Delete associated comments first
    for comment in post.comments:
        await db.delete(comment)

    await db.delete(post)
    await db.commit()



# ── DELETE /api/posts/comments/{comment_id} ──────────────────────────
@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment (author or admin only).

    Note: This route is mounted under /api/feed prefix, so the
    full path is /api/feed/comments/{comment_id}.
    """
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comentario nao encontrado.")

    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Sem permissao para deletar este comentario.")

    await db.delete(comment)
    await db.commit()
