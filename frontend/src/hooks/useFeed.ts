"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { X, ImageIcon, Camera, User } from "lucide-react";
import apiClient from "@/lib/api-client";

const MAX_LENGTH = 5000;

interface UserData {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
}

interface CreatePostModalProps {
  user: UserData | null;
  open: boolean;
  onClose: () => void;
  onSubmit?: (payload: { content: string; isAnonymous: boolean }) => void;
}

function getInitials(user: UserData | null): string {
  if (!user) return "?";
  const source = user.name?.trim() || user.username || "?";
  return source[0]?.toUpperCase() ?? "?";
}

export default function CreatePostModal({ user, open, onClose, onSubmit }: CreatePostModalProps) {
  const router = useRouter();
  const [content, setContent] = useState("");
  const [anonymous, setAnonymous] = useState(false);
  const [sending, setSending] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

  const canPost = content.trim().length > 0 || selectedFile !== null;

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result as string);
      reader.readAsDataURL(file);
    }
  }

  function removeImage() {
    setSelectedFile(null);
    setPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handlePost() {
    if (!canPost || sending) return;

    // ── 1. Chama a API via axios (proxy Next.js, sem CORS) ──────
    try {
      const formData = new FormData();
      formData.append("content", content.trim());
      formData.append("is_anonymous", String(anonymous));
      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      // axios jah tem withCredentials:true + interceptor que anexa
      // o Bearer token automaticamente via apiClient

      const res = await apiClient.post("/api/feed/", formData);
      const newPost = res.data;

      // ── 2. Dispara evento com os dados REAIS do backend ───────
      window.dispatchEvent(new CustomEvent("new-post", { detail: newPost }));
    } catch (err) {
      console.error("[CreatePostModal] erro ao criar post:", err);
      alert(err instanceof Error ? err.message : "Erro ao criar post.");
      setSending(false);
      return;
    }

    // ── 3. Limpa e fecha ─────────────────────────────────────────
    setContent("");
    setAnonymous(false);
    setSending(false);
    setSelectedFile(null);
    setPreview(null);

    onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      handlePost();
    }
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) { removeImage(); onClose(); } }}
    >
        className="flex w-full max-w-[600px] flex-col rounded-2xl border border-zinc-800 bg-black shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <button
              onClick={() => { removeImage(); onClose(); }}
              className="flex h-9 w-9 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-100"
            >
              <X className="h-5 w-5" />
            </button>
            <span className="text-lg font-bold text-zinc-100">Novo Post</span>
          </div>
          {/* Botão Postar removido do topo */}
          <div className="w-9" />
        </div>

        {/* ── Corpo ─────────────────────────────────────────────── */}
        <div className="flex gap-3 px-4 pt-2 pb-1">
          {/* Avatar */}
          <div className="shrink-0">
            {anonymous || !user ? (
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400/20 to-violet-500/20 text-sm font-bold text-violet-400 ring-2 ring-zinc-800">
                <User className="h-5 w-5" />
              </div>
            ) : user.profile_pic ? (
              <div className="relative h-10 w-10 overflow-hidden rounded-full ring-2 ring-zinc-800">
                <Image
                  src={
                    user.profile_pic.startsWith("/")
                      ? user.profile_pic
                      : `/static/uploads/${user.profile_pic}`
                  }
                  alt={user.name || user.username}
                  fill
                  className="object-cover"
                  sizes="40px"
                  unoptimized
                />
              </div>
            ) : (
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500 to-violet-600 text-sm font-bold text-white ring-2 ring-zinc-800">
                {getInitials(user)}
              </div>
            )}
          </div>

          {/* Textarea */}
          <div className="min-w-0 flex-1">
            {!anonymous && user && (
              <p className="mb-1 text-sm font-bold text-zinc-200">
                {user.name || user.username}
              </p>
            )}

            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="O que está acontecendo?"
              maxLength={MAX_LENGTH}
              rows={5}
              autoFocus
              className="w-full resize-none bg-transparent text-xl leading-relaxed text-zinc-100 outline-none placeholder-zinc-600"
            />

            {/* ── Preview da imagem ──────────────────────────────── */}
            {preview && (
              <div className="relative mt-3 overflow-hidden rounded-xl border border-zinc-800">
                <button
                  onClick={removeImage}
                  className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-black/70 text-zinc-300 transition-colors hover:bg-black/90 hover:text-white"
                >
                  <X className="h-4 w-4" />
                </button>
                <Image
                  src={preview}
                  alt="Preview"
                  width={500}
                  height={300}
                  className="max-h-64 w-full object-cover"
                  unoptimized
                />
              </div>
            )}
          </div>
        </div>

        {/* ── Switch Anônimo ────────────────────────────────────── */}
        <div className="flex items-center gap-3 border-b border-zinc-800/60 px-4 py-3">
          <button
            onClick={() => setAnonymous(!anonymous)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              anonymous ? "bg-violet-600" : "bg-zinc-700"
            }`}
          >
            <span
              className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
                anonymous ? "translate-x-[22px]" : "translate-x-[2px]"
              }`}
            />
          </button>
          <span className="text-sm text-zinc-400">
            Postar de forma <span className="font-semibold text-violet-400">anônima</span>?
          </span>
        </div>

        {/* ── Rodapé: Câmera/Foto + Postar ───────────────────────── */}
        <div className="flex items-center justify-between px-4 py-3">
          {/* Botão Câmera/Foto */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              title="Adicionar foto"
              className="flex h-9 w-9 items-center justify-center rounded-full text-emerald-400 transition-colors hover:bg-zinc-900 hover:text-emerald-300"
            >
              <Camera className="h-5 w-5" />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={handleFileSelect}
            />
            {selectedFile && (
              <span className="ml-1 text-xs text-emerald-400/80">1 foto selecionada</span>
            )}
          </div>

          {/* Botão Postar (único, no rodapé) */}
          <button
            onClick={handlePost}
            disabled={!canPost || sending}
            className="rounded-full bg-gradient-to-r from-emerald-500 to-violet-600 px-5 py-2 text-sm font-bold text-white transition-all hover:from-emerald-400 hover:to-violet-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {sending ? "Postando..." : "Postar"}
          </button>
        </div>
      </div>
    </div>
  );
}

