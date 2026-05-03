"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Heart,
  Settings,
  Send,
  UserPlus,
  UserMinus,
  X,
  Users,
  Pencil,
} from "lucide-react";
import apiClient from "@/lib/api-client";

// ── Helpers ──────────────────────────────────────────────────────────
function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".0", "")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(".0", "")}k`;
  return String(n);
}

// ── Converte nome de arquivo em URL absoluta para o next/image ──
function getProfilePicUrl(pic: string | null): string | null {
  if (!pic) return null;
  if (pic.startsWith("http")) return pic;       // URL absoluta
  if (pic.startsWith("/")) return pic;          // já tem barra
  return `/static/uploads/${pic}`;               // nome simples → caminho completo
}

function getUniversityAbbr(university: string | null): string {
  if (!university) return "";
  // Remove parênteses e caracteres não-alfanuméricos, depois pega as iniciais
  const cleanString = university.replace(/[^\w\s]/gi, '');
  return cleanString
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 4);
}

// ── Types ────────────────────────────────────────────────────────────
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

// ── Props ────────────────────────────────────────────────────────────
interface ProfileHeaderProps {
  profile: ProfileData;
  currentUserId: number | undefined;
  onProfileUpdate: (updated: ProfileData) => void;
  onOpenEdit: () => void;
}

export default function ProfileHeader({
  profile,
  currentUserId,
  onProfileUpdate,
  onOpenEdit,
}: ProfileHeaderProps) {
  const [following, setFollowing] = useState(profile.is_following);
  const [followLoading, setFollowLoading] = useState(false);
  const [showActionSheet, setShowActionSheet] = useState(false);
  const [modalType, setModalType] = useState<"followers" | "following" | null>(null);
  const [modalUsers, setModalUsers] = useState<any[]>([]);
  const [modalLoading, setModalLoading] = useState(false);

  const univAbbr = getUniversityAbbr(profile.university);

  // ── Follow / Unfollow via API ───────────────────────────────────
  const handleFollow = async () => {
    if (followLoading) return;
    const prevFollowing = following;
    const prevFollowers = profile.followers_count;
    setFollowing(!following);
    onProfileUpdate({
      ...profile,
      followers_count: following ? prevFollowers - 1 : prevFollowers + 1,
    });
    setFollowLoading(true);
    try {
      if (prevFollowing) {
        await apiClient.delete(`/api/unfollow/${profile.id}`);
      } else {
        await apiClient.post(`/api/follow/${profile.id}`);
      }
    } catch {
      setFollowing(prevFollowing);
      onProfileUpdate({ ...profile, followers_count: prevFollowers });
    } finally {
      setFollowLoading(false);
    }
  };

  // ── Modal de seguidores/seguindo ────────────────────────────────
  const openModal = async (type: "followers" | "following") => {
    setModalType(type);
    setModalLoading(true);
    setModalUsers([]);
    try {
      const response = await apiClient.get(`/users/${profile.username}/${type}`);
      setModalUsers(response.data || []);
    } catch {
      setModalUsers([]);
    } finally {
      setModalLoading(false);
    }
  };

  return (
    <>
      {/* ── Cabeçalho com ícone de configuração no topo direito ── */}
      <header className="relative mx-auto max-w-3xl px-4 pt-8 pb-4 sm:px-8 sm:pt-12">
        {/* Gear icon — canto superior direito */}
        {profile.is_owner && (
          <button
            onClick={() => setShowActionSheet(true)}
            className="absolute right-4 top-4 z-10 flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700/60 bg-zinc-900/80 text-zinc-400 backdrop-blur-sm transition-all hover:bg-zinc-800 hover:text-zinc-200 active:scale-90"
          >
            <Settings className="h-4 w-4" />
          </button>
        )}

        <div className="flex flex-col items-center gap-5 sm:flex-row sm:items-start sm:gap-12">
          {/* Avatar */}
          <div className="relative h-24 w-24 sm:h-28 sm:w-28">
            <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-emerald-400 to-violet-500 p-[3px]">
              <div className="flex h-full w-full items-center justify-center rounded-full bg-black">
                {profile.profile_pic ? (
                  <Image
                    src={getProfilePicUrl(profile.profile_pic)!}
                    alt={profile.name || profile.username}
                    width={112}
                    height={112}
                    className="h-full w-full rounded-full object-cover"
                    unoptimized
                  />
                ) : (
                  <span className="text-3xl font-bold text-zinc-100">
                    {getInitials(profile.name || profile.username)}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Info */}
          <div className="flex-1 text-center sm:text-left">
            {/* Nome principal (grande) */}
            <h1 className="text-xl font-bold text-zinc-100 sm:text-2xl">
              {profile.name || profile.username}
              {profile.is_verified && (
                <span className="ml-1.5 text-sm text-emerald-400">✓</span>
              )}
            </h1>

            {/* @username + badge universidade */}
            <div className="mt-1 flex items-center justify-center gap-2 sm:justify-start">
              <span className="text-sm text-zinc-500">@{profile.username}</span>
              {univAbbr && (
                <span className="rounded-md bg-violet-500/15 px-2 py-0.5 text-[11px] font-medium text-violet-400">
                  {univAbbr}
                </span>
              )}
            </div>

            {/* Bio */}
            {profile.bio && (
              <p className="mt-3 text-sm leading-relaxed text-zinc-400">{profile.bio}</p>
            )}

            {profile.social_link && (
              <a
                href={`https://${profile.social_link}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-block text-sm font-medium text-emerald-400 transition hover:text-emerald-300"
              >
                {profile.social_link}
              </a>
            )}

            {/* Stats — clicáveis */}
            <div className="mt-3 flex justify-center gap-5 text-sm sm:justify-start">
              <span>
                <strong className="text-zinc-100">{formatCount(profile.posts_count)}</strong>{" "}
                <span className="text-zinc-500">Publicações</span>
              </span>
              <button
                onClick={() => openModal("followers")}
                className="transition-colors hover:text-zinc-300"
              >
                <strong className="text-zinc-100">{formatCount(profile.followers_count)}</strong>{" "}
                <span className="text-zinc-500">Seguidores</span>
              </button>
              <button
                onClick={() => openModal("following")}
                className="transition-colors hover:text-zinc-300"
              >
                <strong className="text-zinc-100">{formatCount(profile.following_count)}</strong>{" "}
                <span className="text-zinc-500">Seguindo</span>
              </button>
            </div>

            {/* ── Botões de Ação ──────────────────────────────── */}
            {!profile.is_owner && (
              <div className="mt-5 flex items-center justify-center gap-4 sm:justify-start">
                <button
                  onClick={handleFollow}
                  disabled={followLoading}
                  className={`inline-flex items-center gap-2 rounded-full px-6 py-2 text-sm font-semibold transition-all active:scale-95 disabled:opacity-60 ${
                    following
                      ? "border border-zinc-700 bg-zinc-900 text-zinc-200 hover:border-red-500/50 hover:text-red-400"
                      : "bg-emerald-600 text-white hover:bg-emerald-500"
                  }`}
                >
                  {following ? (
                    <><UserMinus className="h-4 w-4" /> Seguindo</>
                  ) : (
                    <><UserPlus className="h-4 w-4" /> Seguir</>
                  )}
                </button>

                <Link
                  href={`/direct?with_user=${profile.username}`}
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-zinc-900 text-zinc-400 transition-all hover:bg-zinc-800 hover:text-zinc-200 active:scale-90"
                  title="Enviar mensagem"
                >
                  <Send className="h-4 w-4" />
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── Action Sheet (desliza de baixo) ───────────────────── */}
      {showActionSheet && (
        <div
          className="fixed inset-0 z-[70] flex items-end justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setShowActionSheet(false)}
        >
          <div
            className="w-full max-w-lg animate-slide-up rounded-t-2xl border-t border-zinc-800/60 bg-zinc-900 px-5 pb-10 pt-6 shadow-2xl shadow-black/50"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mx-auto mb-6 h-1 w-10 rounded-full bg-zinc-700" />

            <button
              onClick={() => {
                setShowActionSheet(false);
                onOpenEdit();
              }}
              className="flex w-full items-center gap-4 rounded-xl px-4 py-4 text-left text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-800/60"
            >
              <Pencil className="h-5 w-5 text-zinc-400" />
              Editar perfil
            </button>
          </div>
        </div>
      )}

      {/* ── Modal de Seguidores / Seguindo ────────────────────── */}
      {modalType && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm"
          onClick={() => setModalType(null)}
        >
          <div
            className="mx-4 w-full max-w-md rounded-2xl border border-zinc-800/60 bg-zinc-900 shadow-2xl shadow-black/50"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-zinc-800/60 px-5 py-4">
              <h2 className="text-base font-bold text-zinc-100">
                {modalType === "followers" ? "Seguidores" : "Seguindo"}
              </h2>
              <button
                onClick={() => setModalType(null)}
                className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Lista */}
            <div className="max-h-96 overflow-y-auto px-2 py-2">
              {modalLoading ? (
                <div className="flex items-center justify-center py-10">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-400 border-t-transparent" />
                </div>
              ) : modalUsers.length === 0 ? (
                <div className="flex flex-col items-center py-10 text-zinc-500">
                  <Users className="mb-2 h-8 w-8" />
                  <p className="text-sm">
                    {modalType === "followers"
                      ? "Nenhum seguidor ainda."
                      : "Não segue ninguém ainda."}
                  </p>
                </div>
              ) : (
                modalUsers.map((u: any) => (
                  <Link
                    key={u.id}
                    href={`/perfil/${u.username}`}
                    onClick={() => setModalType(null)}
                    className="flex items-center gap-3 rounded-xl px-3 py-3 transition-colors hover:bg-zinc-800/60"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400/30 to-violet-500/30 text-sm font-bold text-violet-400">
                      {getInitials(u.name || u.username)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-zinc-100">
                        {u.name || u.username}
                        {u.is_verified && (
                          <span className="ml-1 text-[10px] text-emerald-400">✓</span>
                        )}
                      </p>
                      <p className="truncate text-xs text-zinc-500">@{u.username}</p>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── CSS para animação slide-up ────────────────────────── */}
      <style jsx>{`
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to { transform: translateY(0); }
        }
        .animate-slide-up {
          animation: slideUp 0.25s ease-out;
        }
      `}</style>
    </>
  );
}
