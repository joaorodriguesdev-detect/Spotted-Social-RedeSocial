"use client";

import { useEffect, useState, useRef, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save, ArrowLeft, ImagePlus, ExternalLink } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

// ── Types ──────────────────────────────────────────────────────────────
interface ProfileData {
  id: number;
  username: string;
  name: string | null;
  university: string | null;
  bio: string | null;
  profile_pic: string | null;
  social_link: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const UNIVERSITIES = [
  "", "UFPR (Federal)", "UTFPR", "PUCPR", "UP (Positivo)",
  "UTP (Tuiuti)", "UniCuritiba", "FAE", "Outra",
];

// ── Page ───────────────────────────────────────────────────────────────
export default function EditarPerfilPage() {
  const router = useRouter();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [socialLink, setSocialLink] = useState("");
  const [university, setUniversity] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Fetch current profile ───────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          credentials: "include",
        });
        if (!res.ok) {
          router.push("/login");
          return;
        }
        const user = await res.json();

        const res2 = await fetch(`${API_BASE}/api/perfil/${user.username}`, {
          credentials: "include",
        });
        if (res2.ok) {
          const data: ProfileData = await res2.json();
          setProfile(data);
          setName(data.name || "");
          setBio(data.bio || "");
          setSocialLink(data.social_link || "");
          setUniversity(data.university || "");
        }
      } catch {
        setError("Erro ao carregar perfil");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  // ── Avatar preview ──────────────────────────────────────────────────
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setError("Imagem muito grande. Máximo 5MB.");
      return;
    }

    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
    setError(null);
  };

  // ── Submit ──────────────────────────────────────────────────────────
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    setSaving(true);
    try {
      const formData = new FormData();
      formData.append("name", name.trim());
      formData.append("bio", bio.trim());
      formData.append("social_link", socialLink.trim());
      formData.append("university", university);
      if (avatarFile) {
        formData.append("profile_pic", avatarFile);
      }

      const res = await fetch(`${API_BASE}/api/perfil/update`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          bio: bio.trim(),
          social_link: socialLink.trim(),
          university,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erro ao salvar" }));
        setError(err.detail || "Erro ao salvar");
        return;
      }

      if (avatarFile) {
        const photoForm = new FormData();
        photoForm.append("file", avatarFile);
        const photoRes = await fetch(`${API_BASE}/api/perfil/update-photo`, {
          method: "PUT",
          credentials: "include",
          body: photoForm,
        });

        if (!photoRes.ok) {
          const err = await photoRes.json().catch(() => ({ detail: "Erro ao salvar foto" }));
          setError(err.detail || "Erro ao salvar foto");
          return;
        }
      }

      setSuccess(true);
      setTimeout(() => {
        if (profile) router.push(`/perfil/${profile.username}`);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  };

  // ── Loading ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-10 h-10 animate-spin text-purple-400" />
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <Link
          href={profile ? `/perfil/${profile.username}` : "/"}
          className="p-2 text-gray-400 hover:text-purple-400 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Editar Perfil</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {profile ? `@${profile.username}` : ""}
          </p>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 rounded-lg bg-red-900/30 border border-red-800/50 px-4 py-3 text-sm text-red-400 font-medium">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-6 rounded-lg bg-emerald-900/30 border border-emerald-800/50 px-4 py-3 text-sm text-emerald-400 font-medium">
          Perfil atualizado com sucesso! Redirecionando…
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* ── Avatar ─────────────────────────────────────────── */}
        <div className="flex items-center gap-6">
          <div className="relative">
            {avatarPreview || profile?.profile_pic ? (
              <Image
                src={
                  avatarPreview ||
                  `${API_BASE}/static/uploads/${profile?.profile_pic}`
                }
                alt="Avatar"
                width={96}
                height={96}
                className="w-24 h-24 rounded-full object-cover border-4 border-purple-900/50"
                unoptimized
              />
            ) : (
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-3xl font-bold text-black">
                {(profile?.name || profile?.username || "?")[0].toUpperCase()}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-purple-600/40 text-purple-300 text-sm hover:bg-purple-800/40 transition-all"
          >
            <ImagePlus className="w-4 h-4" />
            Alterar foto
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </div>

        {/* ── Name ────────────────────────────────────────────── */}
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-1.5">
            Nome
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Seu nome"
            maxLength={80}
            className="w-full bg-gray-800 text-gray-200 border border-gray-700 rounded-xl px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
          />
        </div>

        {/* ── Bio ─────────────────────────────────────────────── */}
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-1.5">
            Bio
          </label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder="Fale um pouco sobre você..."
            rows={3}
            maxLength={300}
            className="w-full bg-gray-800 text-gray-200 border border-gray-700 rounded-xl px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none"
          />
          <p className="text-xs text-gray-600 mt-1">{bio.length}/300</p>
        </div>

        {/* ── University ──────────────────────────────────────── */}
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-1.5">
            Universidade
          </label>
          <select
            value={university}
            onChange={(e) => setUniversity(e.target.value)}
            className="w-full bg-gray-800 text-gray-200 border border-gray-700 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500/50 appearance-none"
          >
            {UNIVERSITIES.map((uni) => (
              <option key={uni} value={uni}>
                {uni || "Selecione..."}
              </option>
            ))}
          </select>
        </div>

        {/* ── Social Link ─────────────────────────────────────── */}
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-1.5 flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
            Link externo
          </label>
          <input
            type="url"
            value={socialLink}
            onChange={(e) => setSocialLink(e.target.value)}
            placeholder="https://seusite.com"
            className="w-full bg-gray-800 text-gray-200 border border-gray-700 rounded-xl px-4 py-3 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
          />
        </div>

        {/* ── Submit ──────────────────────────────────────────── */}
        <div className="flex items-center gap-4 pt-4">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold text-sm transition-all hover:from-purple-500 hover:to-pink-500 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Salvando…
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Salvar alterações
              </>
            )}
          </button>

          <Link
            href={profile ? `/perfil/${profile.username}` : "/"}
            className="text-sm text-gray-500 hover:text-purple-400 transition-colors"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  );
}
