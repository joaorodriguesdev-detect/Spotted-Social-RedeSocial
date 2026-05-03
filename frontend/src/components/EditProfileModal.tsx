"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import { X, Camera, Loader2 } from "lucide-react";
import apiClient from "@/lib/api-client";

// ── Helpers ──────────────────────────────────────────────────────────
function getProfilePicUrl(pic: string | null): string | null {
  if (!pic) return null;
  if (pic.startsWith("http") || pic.startsWith("data:")) return pic;
  if (pic.startsWith("/")) return pic;
  return `/static/uploads/${pic}`;
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
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

interface EditProfileModalProps {
  profile: ProfileData;
  onClose: () => void;
  onSave: (updated: ProfileData) => void;
}

export default function EditProfileModal({
  profile,
  onClose,
  onSave,
}: EditProfileModalProps) {
  const [name, setName] = useState(profile.name || "");
  const [bio, setBio] = useState(profile.bio || "");
  const [saving, setSaving] = useState(false);
  const [previewPic, setPreviewPic] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Selecionar foto ──────────────────────────────────────────────
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Preview local
    const reader = new FileReader();
    reader.onload = (ev) => setPreviewPic(ev.target?.result as string);
    reader.readAsDataURL(file);
    setSelectedFile(file);
  };

  // ── Salvar (tudo em um único FormData) ───────────────────────────
  const handleSave = async () => {
    if (saving) return;
    setSaving(true);

    try {
      // Monta FormData com texto + opcionalmente foto
      const formData = new FormData();
      formData.append("name", name.trim());
      formData.append("bio", bio.trim());
      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      // Envia tudo em UMA chamada para PUT /api/perfil/update
      // O axios define automaticamente Content-Type: multipart/form-data
      // com o boundary correto. NÃO forçar headers manuais.
      const response = await apiClient.put("/api/perfil/update", formData);

      const updatedProfile = response.data as ProfileData;
      onSave(updatedProfile);
      onClose();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Erro ao salvar.";
      alert(msg);
    } finally {
      setSaving(false);
    }
  };

  const currentPic = getProfilePicUrl(previewPic || profile.profile_pic);

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="mx-4 w-full max-w-md rounded-2xl border border-zinc-800/60 bg-zinc-900 shadow-2xl shadow-black/50"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/60 px-5 py-4">
          <h2 className="text-base font-bold text-zinc-100">Editar perfil</h2>
          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-6 px-5 py-6">
          {/* ── Avatar clicável ──────────────────────────────── */}
          <div className="flex justify-center">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="group relative h-24 w-24 overflow-hidden rounded-full"
              title="Alterar foto"
            >
              <div className="flex h-full w-full items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-violet-500 p-[3px]">
                <div className="flex h-full w-full items-center justify-center rounded-full bg-black">
                  {currentPic ? (
                    <Image
                      src={currentPic}
                      alt="Foto de perfil"
                      width={96}
                      height={96}
                      className="h-full w-full rounded-full object-cover"
                    />
                  ) : (
                    <span className="text-2xl font-bold text-zinc-100">
                      {getInitials(name || profile.username)}
                    </span>
                  )}
                </div>
              </div>
              {/* Overlay com ícone de câmera */}
              <div className="absolute inset-0 flex items-center justify-center rounded-full bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                <Camera className="h-6 w-6 text-white" />
              </div>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {/* ── Nome ─────────────────────────────────────────── */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Nome
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={80}
              placeholder="Seu nome"
              className="w-full rounded-xl border border-zinc-700/60 bg-zinc-800/50 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-colors placeholder-zinc-600 focus:border-violet-500/50"
            />
          </div>

          {/* ── Username (read-only) ─────────────────────────── */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Username
            </label>
            <input
              type="text"
              value={`@${profile.username}`}
              disabled
              className="w-full rounded-xl border border-zinc-800/40 bg-zinc-900/30 px-4 py-2.5 text-sm text-zinc-500 outline-none cursor-not-allowed"
            />
          </div>

          {/* ── Bio ──────────────────────────────────────────── */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-zinc-400 uppercase tracking-wider">
              Bio
            </label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              maxLength={150}
              rows={3}
              placeholder="Fale um pouco sobre você..."
              className="w-full resize-none rounded-xl border border-zinc-700/60 bg-zinc-800/50 px-4 py-2.5 text-sm text-zinc-100 outline-none transition-colors placeholder-zinc-600 focus:border-violet-500/50"
            />
            <p className="mt-1 text-right text-xs text-zinc-600">{bio.length}/150</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-zinc-800/60 px-5 py-4">
          <button
            onClick={onClose}
            className="rounded-full px-5 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-zinc-800"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-full bg-emerald-600 px-6 py-2 text-sm font-semibold text-white transition-all hover:bg-emerald-500 active:scale-95 disabled:opacity-50"
          >
            {saving ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Salvando...</>
            ) : (
              "Salvar"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
