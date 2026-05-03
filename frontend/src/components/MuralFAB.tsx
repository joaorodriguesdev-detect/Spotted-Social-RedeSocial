"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Megaphone } from "lucide-react";
import CreateMuralModal from "@/components/CreateMuralModal";
import apiClient from "@/lib/api-client";

/**
 * MuralFAB – Botão flutuante EXCLUSIVO da página do Mural.
 *
 * REGRA ESTRITA:
 *   - Só renderiza se pathname.startsWith("/mural").
 *   - Só abre o CreateMuralModal.
 *   - NUNCA importa CreatePostModal nem CreateEventModal.
 */
export default function MuralFAB() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // ── Validação de rota: só renderiza em /mural ────────────
  if (!pathname.startsWith("/mural")) {
    return null;
  }

  async function handleSubmit(payload: {
    title: string;
    content: string;
    category: string;
    contact_info: string;
  }) {
    const res = await apiClient.post("/api/mural/", payload);
    if (res.status === 201) {
      window.dispatchEvent(new CustomEvent("mural-created"));
      setOpen(false);
      return true;
    }
    return false;
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-24 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-violet-600 to-emerald-500 text-white shadow-[0_8px_32px_rgba(124,58,237,0.35)] transition-all hover:scale-110 hover:shadow-[0_12px_40px_rgba(124,58,237,0.45)] active:scale-95"
        aria-label="Publicar no Mural"
      >
        <Megaphone className="h-6 w-6" />
      </button>

      {open && (
        <CreateMuralModal
          open={open}
          onClose={() => setOpen(false)}
          onSubmit={handleSubmit}
        />
      )}
    </>
  );
}
