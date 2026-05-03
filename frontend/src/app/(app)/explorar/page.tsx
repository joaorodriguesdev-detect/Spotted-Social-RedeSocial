"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Loader2, X } from "lucide-react";
import Image from "next/image";
import SearchBar from "@/components/SearchBar";

// ── Mock imagens (placeholders coloridos) ─────────────────────────────
const MOCK_IMGS = Array.from({ length: 24 }, (_, i) => ({
  id: i + 1,
  src: `https://picsum.photos/seed/spotted${i + 1}/400/400`,
  alt: `Postagem ${i + 1}`,
  likes: Math.floor(Math.random() * 250 + 15),
}));

export default function ExplorarPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center bg-black text-zinc-100">
        <Loader2 className="h-10 w-10 animate-spin text-violet-400" />
      </div>
    );
  }

  const selectedImg = selected !== null ? MOCK_IMGS[selected] : null;

  return (
    <main className="min-h-dvh bg-black text-zinc-100">
      {/* ── Header fixo ──────────────────────────────────────── */}
      <div className="sticky top-0 z-10 border-b border-zinc-800/60 bg-black/90 px-4 py-3 backdrop-blur-xl md:static md:border-b-0 md:px-0 md:pt-6">
        <h1 className="text-xl font-bold text-zinc-100 md:text-2xl">Explorar</h1>
        <p className="mt-0.5 text-xs text-zinc-500">Descubra novos conteúdos</p>
        {/* ── SearchBar ──────────────────────────────────── */}
        <div className="mt-3">
          <SearchBar />
        </div>
      </div>

      {/* ── Grid 3 colunas ────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-[2px] md:gap-1">
        {MOCK_IMGS.map((img, idx) => (
          <button
            key={img.id}
            onClick={() => setSelected(idx)}
            className="group relative aspect-square overflow-hidden bg-zinc-900"
          >
            <Image
              src={img.src}
              alt={img.alt}
              fill
              sizes="(max-width: 768px) 33vw, 25vw"
              className="object-cover transition-transform duration-300 group-hover:scale-105"
              unoptimized
            />
            <div className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/30">
              <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="text-xs font-bold text-white">♥ {img.likes}</span>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* ── Visualizador (Modal) ──────────────────────────────── */}
      {selectedImg && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 backdrop-blur-md"
          onClick={() => setSelected(null)}
        >
          <button
            onClick={() => setSelected(null)}
            className="absolute right-4 top-4 z-10 rounded-full bg-black/60 p-2 text-white transition-colors hover:bg-black/80"
          >
            <X className="h-6 w-6" />
          </button>

          <div
            className="relative max-h-[90vh] max-w-[90vw]"
            onClick={(e) => e.stopPropagation()}
          >
            <Image
              src={selectedImg.src}
              alt={selectedImg.alt}
              width={800}
              height={800}
              className="h-auto max-h-[85vh] w-auto max-w-full rounded-lg object-contain"
              unoptimized
            />
            <div className="mt-3 flex items-center justify-center gap-6 text-sm text-zinc-400">
              <span>♥ {selectedImg.likes} curtidas</span>
              <span>#{selectedImg.id}</span>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
