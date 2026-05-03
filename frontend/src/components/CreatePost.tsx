"use client";

import * as React from "react";
import Image from "next/image";
import { Send } from "lucide-react";
import type { AuthUser } from "@/context/AuthContext";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface CreatePostProps {
  user: AuthUser | null;
  loading?: boolean;
  onSubmit: (payload: { content: string; isAnonymous: boolean }) => Promise<boolean> | boolean;
}

function getInitials(user: AuthUser | null): string {
  const source = user?.name?.trim() || user?.username || "?";
  return source[0]?.toUpperCase() ?? "?";
}

export default function CreatePost({ user, loading = false, onSubmit }: CreatePostProps) {
  const [content, setContent] = React.useState("");
  const [submittingMode, setSubmittingMode] = React.useState<boolean | null>(null);

  const handlePublish = async (isAnonymous: boolean) => {
    const value = content.trim();
    if (!value || loading || submittingMode !== null) return;

    setSubmittingMode(isAnonymous);
    try {
      const ok = await onSubmit({ content: value, isAnonymous });
      if (ok) {
        setContent("");
      }
    } finally {
      setSubmittingMode(null);
    }
  };

  const isBusy = loading || submittingMode !== null;

  return (
    <section className="rounded-[1.75rem] border border-white/10 bg-zinc-950/70 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl sm:p-5">
      <div className="flex gap-4 sm:gap-5">
        <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-full border border-emerald-400/20 bg-zinc-900 ring-2 ring-violet-500/20">
          {user?.profile_pic ? (
            <Image
              src={`${API_BASE}/static/uploads/${user.profile_pic}`}
              alt={user.name || user.username || "Perfil"}
              fill
              className="object-cover"
              sizes="48px"
              unoptimized
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-violet-600 to-emerald-400 text-sm font-bold text-black">
              {getInitials(user)}
            </div>
          )}
        </div>

        <div className="min-w-0 flex-1">
          <textarea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="O que está acontecendo?"
            disabled={isBusy}
            className="min-h-[112px] w-full resize-none rounded-[1.5rem] border border-white/10 bg-zinc-900/50 px-5 py-4 text-[15px] leading-6 text-zinc-100 outline-none placeholder:text-zinc-500 transition-all focus:border-violet-500/50 focus:bg-zinc-900/70 focus:ring-2 focus:ring-violet-500/15 disabled:cursor-not-allowed disabled:opacity-60"
            maxLength={5000}
          />

          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-zinc-500">
              {content.length}/5000
            </p>

            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <button
                type="button"
                onClick={() => handlePublish(true)}
                disabled={isBusy || !content.trim()}
                className="inline-flex items-center justify-center rounded-full bg-zinc-800 px-4 py-2.5 text-sm font-semibold text-zinc-100 transition-all hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submittingMode === true ? (
                  <>
                    <Send className="mr-2 h-4 w-4 animate-pulse" />
                    Spottando…
                  </>
                ) : (
                  "Spottar Anônimo"
                )}
              </button>

              <button
                type="button"
                onClick={() => handlePublish(false)}
                disabled={isBusy || !content.trim()}
                className="inline-flex items-center justify-center rounded-full bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-[0_12px_32px_rgba(124,58,237,0.28)] transition-all hover:bg-violet-500 hover:shadow-[0_16px_40px_rgba(124,58,237,0.32)] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submittingMode === false ? (
                  <>
                    <Send className="mr-2 h-4 w-4 animate-pulse" />
                    Spottando…
                  </>
                ) : (
                  "Spottar"
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

