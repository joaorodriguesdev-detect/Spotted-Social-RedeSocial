"use client";

import { useEffect } from "react";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import PostCard from "@/components/PostCard";
import FeedFAB from "@/components/FeedFAB";
import { usePosts } from "@/context/PostContext";
import { useAuth } from "@/context/AuthContext";

const MOCK_POSTS = [
  {
    id: 1,
    author_name: "Maria Silva",
    author_username: "maria.silva",
    author_profile_pic: null,
    content: "Acabei de apresentar meu TCC e foi um sucesso! 🎉 Queria agradecer a todos que me apoiaram nessa jornada.",
    media_url: null,
    timestamp: new Date(Date.now() - 2 * 3600000).toISOString(),
    likes: 42,
    comment_count: 12,
    is_anonymous: false,
    liked_by_me: false,
    user_id: 1,
  },
  {
    id: 2,
    author_name: null,
    author_username: null,
    author_profile_pic: null,
    content: "Alguém mais acha que a cantina do bloco III está muito cara? Um salgado + suco tá saindo por 18 reais.",
    media_url: null,
    timestamp: new Date(Date.now() - 5 * 3600000).toISOString(),
    likes: 87,
    comment_count: 34,
    is_anonymous: true,
    liked_by_me: false,
    user_id: null,
  },
  {
    id: 3,
    author_name: "Carlos Eduardo",
    author_username: "carlos.edu",
    author_profile_pic: null,
    content: "Rolou um hackathon relâmpago aqui na UP neste fim de semana e meu time ficou em 2º lugar!",
    media_url: null,
    timestamp: new Date(Date.now() - 24 * 3600000).toISOString(),
    likes: 63,
    comment_count: 19,
    is_anonymous: false,
    liked_by_me: false,
    user_id: 2,
  },
  {
    id: 4,
    author_name: "Ana Beatriz",
    author_username: "ana.bia",
    author_profile_pic: null,
    content: "Galera, amanhã tem roda de conversa sobre saúde mental na universidade às 18h no auditório central.",
    media_url: null,
    timestamp: new Date(Date.now() - 36 * 3600000).toISOString(),
    likes: 55,
    comment_count: 8,
    is_anonymous: false,
    liked_by_me: false,
    user_id: 3,
  },
  {
    id: 5,
    author_name: null,
    author_username: null,
    author_profile_pic: null,
    content: "Procurando grupo pra disciplina de Cálculo 3. Alguém aí querendo montar um grupo de estudos?",
    media_url: null,
    timestamp: new Date(Date.now() - 48 * 3600000).toISOString(),
    likes: 31,
    comment_count: 22,
    is_anonymous: true,
    liked_by_me: false,
    user_id: null,
  },
];

export default function HomePage() {
  const router = useRouter();
  const { user, loading } = useAuth();
  const { posts, setPosts } = usePosts();

  // Carrega posts mock na primeira renderização
  useEffect(() => {
    setPosts(MOCK_POSTS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redireciona para /feed (rota canônica do feed)
  useEffect(() => {
    router.replace("/feed");
  }, [router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    );
  }

  function handleLike(postId: number) {
    console.log("Like toggled:", postId);
  }

  return (
    <main className="min-h-screen bg-black pb-28 text-zinc-100">
      <div className="mx-auto w-full max-w-3xl pt-2">
        {posts.map((post) => (
          <PostCard key={post.id} post={post} onLike={handleLike} onComment={(id) => console.log("Comment:", id)} currentUserId={user?.id} />
        ))}
      </div>

      {/* FAB exclusivo do Feed */}
      <FeedFAB />
    </main>
  );
}
