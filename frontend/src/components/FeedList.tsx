"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Image from "next/image";
import {
  Heart,
  MessageCircle,
  Send,
  Loader2,
  UserPlus,
} from "lucide-react";
import { PostCarousel } from "@/components/PostCarousel";

// ── Types (alinhados com o PostResponse do backend) ───────────────────
interface Post {
  id: number;
  content: string;
  media_url: string | null;
  media_urls?: string[];
  timestamp: string | null;
  likes: number;
  user_id: number | null;
  is_anonymous: boolean;
  liked_by_me: boolean;
  author_username: string | null;
  author_name: string | null;
  author_profile_pic: string | null;
  comment_count: number;
}

interface FeedResponse {
  items: Post[];
  has_more: boolean;
  page: number;
  limit: number;
  total_count: number;
}

// ── Helpers ───────────────────────────────────────────────────────────
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

function getInitials(username: string | null): string {
  return (username?.[0]?.toUpperCase() ?? "?");
}

function SkeletonCard() {
  return (
    <article className="rounded-[1.5rem] border border-white/10 bg-zinc-950/60 p-5">
      <div className="flex items-start gap-4 animate-pulse">
        <div className="h-11 w-11 rounded-full bg-zinc-800" />
        <div className="flex-1 space-y-3">
          <div className="h-4 w-32 rounded-full bg-zinc-800" />
          <div className="h-3 w-20 rounded-full bg-zinc-800/80" />
          <div className="space-y-2 pt-2">
            <div className="h-3 w-full rounded-full bg-zinc-800/80" />
            <div className="h-3 w-5/6 rounded-full bg-zinc-800/80" />
          </div>
          <div className="flex gap-3 pt-2">
            <div className="h-8 w-20 rounded-full bg-zinc-800" />
            <div className="h-8 w-20 rounded-full bg-zinc-800" />
          </div>
        </div>
      </div>
    </article>
  );
}

// ── FeedList Component ────────────────────────────────────────────────
export default function FeedList() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const loadingRef = useRef(false);

  const LIMIT = 10;

  // ── Fetch posts ─────────────────────────────────────────────────────
  const fetchPosts = useCallback(
    async (nextPage = 1, append = false) => {
      if (loadingRef.current) return;
      loadingRef.current = true;

      const url = new URL(`${API_BASE}/api/feed/`);
      url.searchParams.set("page", String(nextPage));
      url.searchParams.set("limit", String(LIMIT));

      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
      }

      try {
        const res = await fetch(url.toString(), {
          credentials: "include", // ← envia o cookie JWT httpOnly
          headers: { "Content-Type": "application/json" },
        });

        if (!res.ok) {
          if (res.status === 401) {
            setError("Faça login para ver o feed.");
          } else {
            setError(`Erro ${res.status}`);
          }
          return;
        }

        const data: FeedResponse = await res.json();

        setPosts((prev) => (append ? [...prev, ...data.items] : data.items));
        setHasMore(data.has_more);
        setPage(nextPage);
      } catch (err) {
        console.error("[FeedList.fetchPosts] erro ao carregar feed:", err);
        setError("Erro de conexão com o servidor.");
      } finally {
        setLoading(false);
        setLoadingMore(false);
        loadingRef.current = false;
      }
    },
    []
  );

  // Initial load
  useEffect(() => {
    fetchPosts(1, false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Like toggle ─────────────────────────────────────────────────────
  const toggleLike = async (postId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/feed/${postId}/like`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return;
      const data = await res.json();

      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId
            ? { ...p, liked_by_me: data.liked, likes: data.likes }
            : p
        )
      );
    } catch (err) {
      console.error("[FeedList.toggleLike] erro ao alternar like:", err);
    }
  };

  // ── Load More ───────────────────────────────────────────────────────
  const loadMore = () => {
    if (!hasMore || loadingMore) return;
    fetchPosts(page + 1, true);
  };

  // ── Render States ───────────────────────────────────────────────────
  if (loading && posts.length === 0) {
    return (
      <div className="mx-auto w-full max-w-2xl px-4 py-8 space-y-4">
        <div className="rounded-[1.5rem] border border-white/10 bg-zinc-950/60 p-5 text-sm text-zinc-400">
          Carregando feed…
        </div>
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  if (error && posts.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] px-4">
        <div className="max-w-sm rounded-xl border border-red-800/40 bg-red-950/40 p-6 text-center">
          <p className="text-red-400 font-medium">{error}</p>
          <button
            onClick={() => fetchPosts(1, false)}
            className="mt-4 px-4 py-2 rounded-lg bg-red-800/40 text-red-300 text-sm hover:bg-red-800/60 transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6 px-4 py-8 text-zinc-100">
      {/* ── Header ───────────────────────────────────────────── */}
      <div className="border-b border-purple-900/40 pb-4">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Feed Global
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          Posts de quem você segue + Spotted
        </p>
      </div>

      {/* ── Post List ────────────────────────────────────────── */}
      <div className="space-y-5">
        {posts.length === 0 && !loading ? (
          <div className="space-y-4">
            <div className="rounded-[1.5rem] border border-white/10 bg-zinc-950/60 p-5 text-center text-sm text-zinc-400">
              Nenhum post encontrado. Aguarde ou seja o primeiro a publicar.
            </div>
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : null}

        {posts.map((post) => (
          <article
            key={post.id}
            className="group relative rounded-xl border border-purple-900/30 bg-gray-900/70 backdrop-blur-sm p-5 transition-all duration-300 hover:border-purple-500/40 hover:shadow-[0_0_25px_-8px_rgba(168,85,247,0.4)]"
          >
            {/* ── Author + Metadata ──────────────────────────── */}
            <div className="flex items-center gap-3 mb-3">
              {/* Avatar */}
              <div
                className={`w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold text-black shrink-0 ${
                  post.is_anonymous
                    ? "bg-gray-700 text-gray-400"
                    : "bg-gradient-to-br from-purple-500 to-pink-500"
                }`}
              >
                {post.is_anonymous ? "?" : getInitials(post.author_username)}
              </div>

              {/* Name + Time */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-200 truncate">
                  {post.is_anonymous
                    ? "Anônimo"
                    : post.author_name || post.author_username}
                </p>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{timeAgo(post.timestamp)}</span>
                  {!post.is_anonymous && post.author_username && (
                    <span>@{post.author_username}</span>
                  )}
                </div>
              </div>

              {/* Follow badge (só exemplo visual) */}
              {!post.is_anonymous && (
                <button
                  className="text-gray-500 hover:text-purple-400 transition-colors p-1"
                  title="Seguir"
                >
                  <UserPlus className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* ── Content ────────────────────────────────────── */}
            <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap break-words">
              {post.content}
            </p>

            {/* ── Media ──────────────────────────────────────── */}
            {post.media_urls && post.media_urls.length > 0 ? (
              <div className="mt-3">
                <PostCarousel images={post.media_urls} />
              </div>
            ) : post.media_url ? (
              <div className="mt-3 rounded-lg overflow-hidden border border-purple-900/20">
                <Image
                  src={`${API_BASE}/static/uploads/${post.media_url}`}
                  alt="Mídia do post"
                  width={600}
                  height={400}
                  className="w-full h-auto object-cover max-h-[500px]"
                  unoptimized
                />
              </div>
            ) : null}

            {/* ── Actions ────────────────────────────────────── */}
            <div className="flex items-center gap-6 mt-4 pt-3 border-t border-purple-900/20">
              <button
                onClick={() => toggleLike(post.id)}
                className={`flex items-center gap-1.5 text-sm transition-all ${
                  post.liked_by_me
                    ? "text-pink-400 drop-shadow-[0_0_6px_rgba(236,72,153,0.5)]"
                    : "text-gray-500 hover:text-pink-400"
                }`}
              >
                <Heart
                  className="w-4 h-4"
                  fill={post.liked_by_me ? "currentColor" : "none"}
                />
                <span>{post.likes}</span>
              </button>

              <button className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-cyan-400 transition-colors">
                <MessageCircle className="w-4 h-4" />
                <span>{post.comment_count}</span>
              </button>
            </div>
          </article>
        ))}
      </div>

      {/* ── Load More ────────────────────────────────────────── */}
      {hasMore && posts.length > 0 && (
        <div className="flex justify-center pt-4">
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-purple-700 to-pink-700 text-white font-semibold text-sm transition-all duration-300 hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-purple-900/20"
          >
            {loadingMore ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Carregando…
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Carregar mais
              </>
            )}
          </button>
        </div>
      )}

      {!hasMore && posts.length > 0 && (
        <p className="text-center text-gray-600 text-sm pt-4">
          — Você já viu todos os posts —
        </p>
      )}
    </div>
  );
}
