"use client";

import { useEffect, useState, useCallback } from "react";
import PostCard from "@/components/PostCard";
import SectionTabs from "@/components/SectionTabs";
import { useAuth } from "@/context/AuthContext";
import type { Post } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function FeedPage() {
  const { user } = useAuth();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);

  // ── Busca posts da API ──────────────────────────────────────────────
  const fetchPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/feed/?page=1&limit=50`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setPosts(data.items ?? []);
      }
    } catch (err) {
      console.error("[FeedPage] erro ao carregar feed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Carrega posts ao montar
  useEffect(() => {
    fetchPosts();
  }, [fetchPosts]);

  // Escuta evento "new-post" disparado pelo CreatePostModal
  useEffect(() => {
    function handler(e: CustomEvent) {
      const newPost = e.detail as Post;
      setPosts((prev) => [newPost, ...prev]);
    }
    window.addEventListener("new-post", handler as EventListener);
    return () => window.removeEventListener("new-post", handler as EventListener);
  }, []);

  // ── Like ─────────────────────────────────────────────────────────────
  async function handleLike(postId: number) {
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
            ? { ...p, liked_by_me: data.liked as boolean, likes: data.likes as number }
            : p
        )
      );
    } catch (err) {
      console.error("[FeedPage] erro no like:", err);
    }
  }

  return (
    <main className="min-h-screen bg-black text-zinc-100 pb-28">
      <SectionTabs />
      <div className="mx-auto w-full max-w-3xl pt-2 min-h-[calc(100vh-12rem)]">
        {loading ? (
          <div className="p-8 text-center text-zinc-500">Carregando...</div>
        ) : posts.length === 0 ? (
          <div className="p-8 text-center text-zinc-500">Nenhum post ainda. Seja o primeiro!</div>
        ) : (
          posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onLike={handleLike}
              onComment={(id) => console.log("Comment:", id)}
              currentUserId={user?.id}
            />
          ))
        )}
      </div>
    </main>
  );
}
