"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import {
  Heart,
  MessageCircle,
  ImageIcon,
  Star,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import PostCard from "@/components/PostCard";
import ProfileHeader from "@/components/ProfileHeader";
import EditProfileModal from "@/components/EditProfileModal";
import { usePosts } from "@/context/PostContext";
import { useAuth } from "@/context/AuthContext";
import apiClient from "@/lib/api-client";

const getStaticUrl = (url: string | null) => {
  if (!url) return "";
  if (url.startsWith("http") || url.startsWith("/")) return url;
  return `/static/uploads/${url}`;
};

type TabId = "posts" | "replies" | "highlights" | "photos";

const TABS: { id: TabId; label: string; icon: typeof Heart }[] = [
  { id: "posts", label: "Publicacoes", icon: Heart },
  { id: "replies", label: "Respostas", icon: MessageCircle },
  { id: "highlights", label: "Destaques", icon: Star },
  { id: "photos", label: "Fotos", icon: ImageIcon },
];

interface ProfileData {
  id: number;
  username: string;
  name: string | null;
  university: string | null;
  bio: string | null;
  profile_pic: string | null;
  social_link: string | null;
  is_admin: boolean;
  is_verified: boolean;
  created_at: string | null;
  followers_count: number;
  following_count: number;
  posts_count: number;
  recent_posts: any[];
  is_owner: boolean;
  is_following: boolean;
}

export default function PerfilPage() {
  const { user: authUser, refresh: refreshAuth } = useAuth();
  const params = useParams();
  const username = (params?.username as string) || "";
  const { userPosts } = usePosts();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("posts");
  const [editModalOpen, setEditModalOpen] = useState(false);

  // Busca o perfil na API quando o username muda
  useEffect(() => {
    if (!username) return;

    const fetchProfile = async () => {
      setLoadingProfile(true);
      setError(null);
      try {
        const response = await apiClient.get(`/api/perfil/${username}`);
        const data = response.data as ProfileData;
        setProfile(data);
      } catch (err: any) {
        const detail = err?.response?.data?.detail;
        if (detail) {
          setError(detail);
        } else if (err?.response?.status === 404) {
          setError("Usuario nao encontrado.");
        } else {
          setError("Erro ao carregar perfil.");
        }
      } finally {
        setLoadingProfile(false);
      }
    };

    fetchProfile();
  }, [username]);

  // Filtra posts com midia para a aba "Fotos"
  const profilePosts = profile?.recent_posts || [];
  const mediaPosts = profilePosts.filter((p: any) => p.media_urls && p.media_urls.length > 0);

  function handleLike(postId: number) {
    console.log("Like toggled:", postId);
  }

  // Estados de carregamento / erro
  if (loadingProfile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-black text-zinc-400">
        <Heart className="h-12 w-12 text-zinc-600" />
        <p className="text-sm">{error || "Perfil nao encontrado."}</p>
        <Link
          href="/feed"
          className="rounded-full bg-zinc-900 px-5 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
        >
          Voltar para o Feed
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-zinc-100">
      {/* Header do Perfil (componente extraido) */}
      <ProfileHeader
        profile={profile}
        currentUserId={authUser?.id}
        onProfileUpdate={(updated) => setProfile(updated)}
        onOpenEdit={() => setEditModalOpen(true)}
      />

      {/* Abas estilo Twitter/X */}
      <div className="border-b border-zinc-800/60">
        <div className="mx-auto flex max-w-3xl">
          {TABS.map((item) => {
            const isActive = tab === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setTab(item.id)}
                className={`relative flex flex-1 items-center justify-center gap-2 px-2 py-4 text-sm font-medium transition-colors ${
                  isActive ? "text-zinc-100" : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/50"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-emerald-400" : ""}`} />
                <span className="hidden sm:inline">{item.label}</span>
                {isActive && (
                  <span className="absolute bottom-0 left-1/4 right-1/4 h-[3px] rounded-full bg-emerald-500" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Conteudo das Abas */}
      <main className="mx-auto max-w-3xl pb-32">
        {/* Publicacoes */}
        {tab === "posts" && (
          <div>
            {profilePosts.length === 0 ? (
              <div className="flex flex-col items-center py-20 text-zinc-500">
                <Heart className="mb-3 h-10 w-10" />
                <p className="text-sm">Nenhuma publicacao ainda.</p>
              </div>
            ) : (
              profilePosts.map((post: any) => (
                <PostCard
                  key={post.id}
                  post={post}
                  onLike={handleLike}
                  onComment={(id) => console.log("Comment:", id)}
                  currentUserId={authUser?.id}
                />
              ))
            )}
          </div>
        )}

        {/* Respostas */}
        {tab === "replies" && (
          <div className="px-4">
            <div className="flex flex-col items-center py-20 text-zinc-500">
              <MessageCircle className="mb-3 h-10 w-10" />
              <p className="text-sm">Nenhuma resposta ainda.</p>
            </div>
          </div>
        )}

        {/* Destaques */}
        {tab === "highlights" && (
          <div className="px-4">
            <div className="flex flex-col items-center py-20 text-zinc-500">
              <Star className="mb-3 h-10 w-10" />
              <p className="text-sm">Nenhum destaque ainda.</p>
            </div>
          </div>
        )}

        {/* Fotos */}
        {tab === "photos" && (
          <div className="px-4 pt-4">
            {mediaPosts.length === 0 ? (
              <div className="flex flex-col items-center py-20 text-zinc-500">
                <ImageIcon className="mb-3 h-10 w-10" />
                <p className="text-sm">Nenhuma foto publicada ainda.</p>
              </div>
            ) : (
              <div className="grid grid-cols-3 gap-1 sm:gap-2">
                {mediaPosts.map((post: any) => (
                  <Link
                    key={post.id} // A chave já é única
                    href="#"
                    className="group relative aspect-square overflow-hidden rounded-md bg-zinc-900 sm:rounded-lg"
                  >
                    <img
                      src={getStaticUrl(post.media_urls[0])} // Usamos a primeira imagem e a função helper
                      alt={`Foto ${post.id}`}
                      className="h-full w-full object-cover transition-all duration-300 group-hover:scale-105 group-hover:brightness-50"
                    />
                    <div className="absolute inset-0 flex items-center justify-center gap-4 opacity-0 transition-opacity group-hover:opacity-100">
                      <span className="inline-flex items-center gap-1 text-sm font-bold text-white">
                        <Heart className="h-5 w-5 fill-white" />
                        {post.likes}
                      </span>
                      <span className="inline-flex items-center gap-1 text-sm font-bold text-white">
                        <MessageCircle className="h-5 w-5 fill-white" />
                        {post.comment_count}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modal de Edicao de Perfil */}
      {editModalOpen && (
        <EditProfileModal
          profile={profile}
          onClose={() => setEditModalOpen(false)}
          onSave={async (updated) => {
            setProfile(updated);
            setEditModalOpen(false);
            // Revalida o estado global do usuario autenticado
            // para sidebar, footer, CreatePostModal e feed
            await refreshAuth();
          }}
        />
      )}
    </div>
  );
}
