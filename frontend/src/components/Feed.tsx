"use client";

import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useFeed } from "@/hooks/useFeed";
import type { Post } from "@/types";
import PostCard from "@/components/PostCard";

function FeedSkeletonCard() {
  return (
    <article className="rounded-[1.75rem] border border-white/10 bg-zinc-950/60 p-5">
      <div className="flex items-start gap-4 animate-pulse">
        <div className="h-12 w-12 rounded-full bg-zinc-800" />
        <div className="flex-1 space-y-4">
          <div className="space-y-2">
            <div className="h-4 w-36 rounded-full bg-zinc-800" />
            <div className="h-3 w-24 rounded-full bg-zinc-800/80" />
          </div>
          <div className="space-y-2">
            <div className="h-3 w-full rounded-full bg-zinc-800/80" />
            <div className="h-3 w-5/6 rounded-full bg-zinc-800/80" />
            <div className="h-3 w-2/3 rounded-full bg-zinc-800/80" />
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

export default function Feed() {
  const { user } = useAuth();
  const { posts, hasMore, loading, error, fetchPosts, fetchMorePosts, createPost, toggleLike } = useFeed();

  useEffect(() => {
    fetchPosts(1, 10);
  }, [fetchPosts]);

  const handleCreatePost = async (payload: { content: string; isAnonymous: boolean }) => {
    const created = await createPost({
      content: payload.content,
      is_anonymous: payload.isAnonymous,
    });

    return Boolean(created);
  };

  const handleLike = async (postId: number) => {
    await toggleLike(postId);
  };

  return (
    <main className="min-h-screen bg-black px-4 pb-28 pt-8 text-zinc-100">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        

        <section className="space-y-5">
          

          {error ? (
            <div
              className={`rounded-[1.5rem] border border-red-500/20 bg-red-950/30 p-5 text-sm text-red-300 ${
                posts.length > 0 ? "" : ""
              }`}
            >
              <p className="font-semibold">NÃ£o foi possÃ­vel carregar o feed.</p>
              <p className="mt-1 text-red-200/80">{error}</p>
              <button
                type="button"
                onClick={() => fetchPosts(1, 10)}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-red-500/15 px-4 py-2 font-semibold text-red-200 transition-colors hover:bg-red-500/25"
              >
                <Loader2 className="h-4 w-4" />
                Tentar novamente
              </button>
            </div>
          ) : null}

          {loading && posts.length === 0 ? (
            <div className="space-y-4">
              <FeedSkeletonCard />
              <FeedSkeletonCard />
              <FeedSkeletonCard />
            </div>
          ) : posts.length > 0 ? (
            <div className="space-y-4">
              {posts.map((post: Post) => (
                <PostCard key={post.id} post={post} onLike={handleLike} currentUserId={user?.id} />
              ))}

              {hasMore ? (
                <div className="flex justify-center pt-2">
                  <button
                    type="button"
                    onClick={() => fetchMorePosts(10)}
                    disabled={loading}
                    className="inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_32px_rgba(124,58,237,0.24)] transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Carregandoâ€¦
                      </>
                    ) : (
                      "Carregar mais"
                    )}
                  </button>
                </div>
              ) : (
                <p className="pt-2 text-center text-sm text-zinc-500">
                  â€” VocÃª jÃ¡ viu todos os posts â€”
                </p>
              )}
            </div>
          ) : (
            <div className="rounded-[1.5rem] border border-white/10 bg-zinc-950/60 p-8 text-center text-sm text-zinc-400">
              Ainda nÃ£o hÃ¡ publicaÃ§Ãµes no feed. Seja o primeiro a spottar.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}


