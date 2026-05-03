"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Image from "next/image";
import {
  Heart,
  MessageCircle,
  Repeat2,
  BarChart3,
  MoreHorizontal,
  Trash2,
  Pencil,
  Check,
  X,
} from "lucide-react";
import type { Post, Comment, LikeResponse } from "@/types";
import apiClient from "@/lib/api-client";

// Helper para resolver URLs de avatar (mesmo padrão do ProfileHeader)
function getProfilePicUrl(pic: string | null): string | null {
  if (!pic) return null;
  if (pic.startsWith("http") || pic.startsWith("data:")) return pic;
  if (pic.startsWith("/")) return pic;
  return `/static/uploads/${pic}`;
}

import { PostCarousel } from "@/components/PostCarousel";

interface PostCardProps {
  post: Post;
  onLike: (postId: number) => Promise<void> | void;
  onComment?: (postId: number) => void;
  /** ID do usuário logado (vindo do AuthContext) para verificação de autoria */
  currentUserId: number | null | undefined;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

function getInitials(value: string | null): string {
  return value?.trim()?.[0]?.toUpperCase() ?? "?";
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".0", "")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".0", "")}k`;
  return String(n);
}

// ── Dropdown Component ───────────────────────────────────────────
function DropdownMenu({
  items,
  onClose,
}: {
  items: { icon: typeof Trash2; label: string; onClick: () => void; danger?: boolean }[];
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="absolute right-0 top-8 z-50 min-w-[180px] overflow-hidden rounded-xl border border-zinc-700/60 bg-zinc-900 shadow-2xl shadow-black/50"
    >
      {items.map((item, i) => (
        <button
          key={i}
          onClick={() => { item.onClick(); onClose(); }}
          className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm font-medium transition-colors ${
            item.danger
              ? "text-red-400 hover:bg-red-500/10"
              : "text-zinc-300 hover:bg-zinc-800"
          }`}
        >
          <item.icon className={`h-4 w-4 ${item.danger ? "text-red-400" : "text-zinc-500"}`} />
          {item.label}
        </button>
      ))}
    </div>
  );
}



export default function PostCard({ post, onLike, currentUserId }: PostCardProps) {
  const [liked, setLiked] = useState(post.liked_by_me);
  const [likeCount, setLikeCount] = useState(post.likes);
  const [commentsOpen, setCommentsOpen] = useState(false);
  const [commentText, setCommentText] = useState("");
  const [comments, setComments] = useState<Comment[]>([]);
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [submittingComment, setSubmittingComment] = useState(false);
  const [postMenuOpen, setPostMenuOpen] = useState(false);
  const [editingCommentId, setEditingCommentId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");

  /** ── Verificação estrita de autoria ─────────────────────────────── */
  const isAuthor = currentUserId != null && post.user_id != null && post.user_id === currentUserId;

  const displayName = post.is_anonymous
    ? "Anônimo"
    : post.author_name || post.author_username || "Usuário";

  const subtitle = post.is_anonymous
    ? ""
    : `@${post.author_username || "usuario"}`;

  // ── Like com optimistic update ─────────────────────────────────────
  const handleLike = useCallback(async () => {
    // Optimistic: atualiza imediatamente
    const prevLiked = liked;
    const prevCount = likeCount;
    setLiked(!liked);
    setLikeCount((c) => (liked ? c - 1 : c + 1));

    try {
      const response = await apiClient.post<LikeResponse>(
        `/api/feed/${post.id}/like`
      );
      // Aplica valor real da API (corrige se necessário)
      setLiked(response.data.liked);
      setLikeCount(response.data.likes);
    } catch {
      // Reverte optimistic update em caso de erro
      setLiked(prevLiked);
      setLikeCount(prevCount);
    }
  }, [post.id, liked, likeCount]);

  // ── Buscar comentários da API ──────────────────────────────────────
  const fetchComments = useCallback(async () => {
    setCommentsLoading(true);
    try {
      const response = await apiClient.get<Comment[]>(
        `/api/feed/${post.id}/comments`
      );
      setComments(response.data || []);
    } catch {
      setComments([]);
    } finally {
      setCommentsLoading(false);
    }
  }, [post.id]);

  // Quando abre a seção de comentários, busca do servidor
  useEffect(() => {
    if (commentsOpen && comments.length === 0 && !commentsLoading) {
      fetchComments();
    }
  }, [commentsOpen, comments.length, commentsLoading, fetchComments]);

  // ── Enviar comentário com optimistic update ────────────────────────
  const handleCommentSend = useCallback(async () => {
    if (!commentText.trim() || submittingComment) return;

    const text = commentText.trim();
    setCommentText("");
    setSubmittingComment(true);

    // Optimistic: adiciona localmente
    const tempId = -Date.now();
    const optimisticComment: Comment = {
      id: tempId,
      post_id: post.id,
      content: text,
      username: "Você",
      user_id: currentUserId ?? null,
      timestamp: new Date().toISOString(),
      is_edited: false,
    };
    setComments((prev) => [...prev, optimisticComment]);

    try {
      const response = await apiClient.post<Comment>(
        `/api/feed/${post.id}/comment`,
        { content: text }
      );
      // Substitui o comentário otimista pelo real
      setComments((prev) =>
        prev.map((c) => (c.id === tempId ? response.data : c))
      );
    } catch {
      // Reverte: remove o comentário otimista
      setComments((prev) => prev.filter((c) => c.id !== tempId));
      setCommentText(text); // Devolve o texto pro input
    } finally {
      setSubmittingComment(false);
    }
  }, [commentText, submittingComment, post.id, currentUserId]);

  // ── Deletar comentário via API ─────────────────────────────────────
  const handleDeleteComment = useCallback(async (commentId: number) => {
    // Só deleta do backend se não for um comentário otimista (tempId < 0)
    if (commentId > 0) {
      try {
        await apiClient.delete(`/api/feed/comments/${commentId}`);
      } catch {
        // Se falhar, mantém o comentário
        return;
      }
    }
    setComments((prev) => prev.filter((c) => c.id !== commentId));
  }, []);

  function handleEditComment(comment: Comment) {
    setEditingCommentId(comment.id);
    setEditText(comment.content);
  }

  function handleSaveEdit(commentId: number) {
    if (!editText.trim()) return;
    setComments((prev) =>
      prev.map((c) =>
        c.id === commentId
          ? { ...c, content: editText.trim(), is_edited: true }
          : c
      )
    );
    setEditingCommentId(null);
    setEditText("");
  }

  function handleCancelEdit() {
    setEditingCommentId(null);
    setEditText("");
  }

  function handleDeletePost() {
    console.log("Post apagado:", post.id);
  }

  // Função de denúncia pode ser adicionada futuramente como ação pública

  return (
    <article className="border-b border-zinc-800/50 px-4 py-3 transition-colors hover:bg-zinc-900/30">
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
            post.is_anonymous
              ? "bg-zinc-800 text-zinc-500"
              : "bg-gradient-to-br from-emerald-400/30 to-violet-500/30 text-violet-400"
          }`}
        >
          {post.is_anonymous || !post.author_profile_pic ? (
            post.is_anonymous ? "?" : getInitials(post.author_username || post.author_name)
          ) : (
            <Image
              src={getProfilePicUrl(post.author_profile_pic)!}
              alt={displayName}
              width={40}
              height={40}
              className="h-full w-full rounded-full object-cover"
              unoptimized
            />
          )}
        </div>

        {/* Conteúdo */}
        <div className="min-w-0 flex-1">
          {/* Header: Nome + @ + tempo + menu */}
          <div className="flex items-center justify-between gap-1 text-sm leading-5">
            <div className="flex items-center gap-1 min-w-0">
              <span className="max-w-[160px] truncate font-bold text-zinc-100">{displayName}</span>
              {subtitle && <span className="truncate text-zinc-500">{subtitle}</span>}
              <span className="text-zinc-600">·</span>
              <span className="shrink-0 text-zinc-500">{timeAgo(post.timestamp)}</span>
            </div>

            {/* ── Menu de três pontinhos do Post ──────────────── */}
            {isAuthor && (
              <div className="relative shrink-0">
                <button
                  onClick={() => setPostMenuOpen(!postMenuOpen)}
                  className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
                {postMenuOpen && (
                  <DropdownMenu
                    onClose={() => setPostMenuOpen(false)}
                    items={[
                      { icon: Trash2, label: "Apagar Post", onClick: handleDeletePost, danger: true },
                    ]}
                  />
                )}
              </div>
            )}
          </div>

          <p className="mt-0.5 whitespace-pre-wrap break-words text-[15px] leading-5 text-zinc-300">
            {post.content}
          </p>

          {post.media_urls && post.media_urls.length > 0 ? (
            <div className="mt-3">
              <PostCarousel images={post.media_urls} />
            </div>
          ) : post.media_url ? (
            <div className="mt-3 overflow-hidden rounded-2xl border border-zinc-800/60 bg-zinc-900/50">
              <Image
                src={post.media_url}
                alt="Mídia do post"
                width={600}
                height={400}
                className="h-auto w-full object-cover max-h-[500px]"
                unoptimized
              />
            </div>
          ) : null}

          {/* Ações */}
          <div className="mt-2 flex max-w-md items-center justify-between">
            <button
              onClick={() => setCommentsOpen(!commentsOpen)}
              className={`group flex items-center gap-1.5 rounded-full px-2 py-1.5 transition-colors ${
                commentsOpen ? "text-violet-400" : "text-zinc-500 hover:text-violet-400"
              }`}
            >
              <MessageCircle className="h-[18px] w-[18px]" />
              <span className="text-xs tabular-nums">{formatCount(post.comment_count)}</span>
            </button>

            <button className="group flex items-center gap-1.5 rounded-full px-2 py-1.5 text-zinc-500 transition-colors hover:text-emerald-400">
              <Repeat2 className="h-[18px] w-[18px]" />
            </button>

            <button
              onClick={handleLike}
              className={`group flex items-center gap-1.5 rounded-full px-2 py-1.5 transition-colors ${
                liked ? "text-violet-400" : "text-zinc-500 hover:text-violet-400"
              }`}
            >
              <Heart className={`h-[18px] w-[18px] ${liked ? "fill-violet-400" : ""}`} />
              <span className="text-xs tabular-nums">{formatCount(likeCount)}</span>
            </button>

            <button className="group flex items-center gap-1.5 rounded-full px-2 py-1.5 text-zinc-500 transition-colors hover:text-emerald-400">
              <BarChart3 className="h-[18px] w-[18px]" />
              <span className="text-xs tabular-nums">{post.likes}</span>
            </button>
          </div>

          {/* Seção de Comentários (expansível) */}
          {commentsOpen && (
            <div className="mt-3 border-t border-zinc-800/40 pt-3">
              {commentsLoading ? (
                <p className="py-4 text-center text-xs text-zinc-600">Carregando comentários...</p>
              ) : comments.length === 0 ? (
                <p className="py-4 text-center text-xs text-zinc-600">Nenhum comentário ainda.</p>
              ) : (
                <div className="space-y-3">
                  {comments.map((c) => {
                    const isCommentAuthor = currentUserId != null && c.user_id != null && c.user_id === currentUserId;
                    const isEditing = editingCommentId === c.id;
                    const isOptimistic = c.id < 0; // IDs temporários são negativos

                    return (
                      <div key={c.id} className={`flex items-start gap-2 ${isOptimistic ? "opacity-60" : ""}`}>
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400/20 to-violet-500/20 text-[10px] font-bold text-violet-400">
                          {getInitials(c.username)}
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-semibold text-zinc-200">
                              {c.username}
                              <span className="ml-2 font-normal text-zinc-600">
                                {timeAgo(c.timestamp)}
                                {isOptimistic && " · enviando..."}
                              </span>
                            </p>

                            {/* Menu de três pontinhos do comentário */}
                            <CommentMenu
                              isAuthor={isCommentAuthor}
                              onEdit={() => handleEditComment(c)}
                              onDelete={() => handleDeleteComment(c.id)}
                            />
                          </div>

                          {isEditing ? (
                            <div className="mt-1 flex items-center gap-2">
                              <input
                                type="text"
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-1.5 text-sm text-zinc-100 outline-none transition-colors focus:border-violet-500/50"
                                autoFocus
                                onKeyDown={(e) => {
                                  if (e.key === "Enter") handleSaveEdit(c.id);
                                  if (e.key === "Escape") handleCancelEdit();
                                }}
                              />
                              <button onClick={() => handleSaveEdit(c.id)} className="rounded-full p-1 text-emerald-400 transition-colors hover:bg-zinc-800">
                                <Check className="h-4 w-4" />
                              </button>
                              <button onClick={handleCancelEdit} className="rounded-full p-1 text-zinc-500 transition-colors hover:bg-zinc-800">
                                <X className="h-4 w-4" />
                              </button>
                            </div>
                          ) : (
                            <p className="mt-0.5 text-sm text-zinc-300">
                              {c.content}
                              {c.is_edited && (
                                <span className="ml-1 text-[10px] italic text-zinc-600">(comentário modificado)</span>
                              )}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Input de novo comentário */}
              <div className="mt-3 flex items-center gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-500">
                  {getInitials(currentUserId ? "" : "V") || "V"}
                </div>
                <div className="flex flex-1 items-center gap-2 rounded-full border border-zinc-800/60 bg-zinc-900/50 px-4 py-1.5 transition-colors focus-within:border-violet-500/50">
                  <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Digite sua resposta..."
                    className="w-full bg-transparent text-sm text-zinc-100 outline-none placeholder-zinc-600"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleCommentSend();
                      }
                    }}
                  />
                  <button
                    onClick={handleCommentSend}
                    disabled={!commentText.trim() || submittingComment}
                    className="shrink-0 text-xs font-semibold text-emerald-400 transition-colors hover:text-emerald-300 disabled:opacity-40"
                  >
                    {submittingComment ? "Enviando..." : "Responder"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

// ── CommentMenu (subcomponente) ───────────────────────────────────
/** Só renderiza o menu de três pontinhos se o usuário for o autor do comentário. */
function CommentMenu({
  isAuthor,
  onEdit,
  onDelete,
}: {
  isAuthor: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);

  // ── Não renderiza nada se não for o autor ───────────────────
  if (!isAuthor) return null;

  return (
    <div className="relative shrink-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex h-6 w-6 items-center justify-center rounded-full text-zinc-600 transition-colors hover:bg-zinc-800 hover:text-zinc-300"
      >
        <MoreHorizontal className="h-3.5 w-3.5" />
      </button>
      {open && (
        <DropdownMenu
          onClose={() => setOpen(false)}
          items={[
            { icon: Pencil, label: "Editar Comentário", onClick: onEdit },
            { icon: Trash2, label: "Excluir Comentário", onClick: onDelete, danger: true },
          ]}
        />
      )}
    </div>
  );
}
