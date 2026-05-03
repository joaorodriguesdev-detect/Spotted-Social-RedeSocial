"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { CalendarPlus } from "lucide-react";
import CreateEventModal from "@/components/CreateEventModal";
import apiClient from "@/lib/api-client";

/**
 * EventFAB – Botão flutuante EXCLUSIVO da página de Eventos.
 *
 * REGRA ESTRITA:
 *   - Só renderiza se pathname.startsWith("/eventos").
 *   - Só abre o CreateEventModal.
 *   - NUNCA importa CreatePostModal nem CreateMuralModal.
 */
export default function EventFAB() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // ── Validação de rota: só renderiza em /eventos ──────────
  if (!pathname.startsWith("/eventos")) {
    return null;
  }

  async function handleSubmit(payload: {
    title: string;
    description: string;
    event_date: string;
    location: string;
    category?: string;
  }) {
    const res = await apiClient.post("/api/events/", payload);
    if (res.status === 201) {
      window.dispatchEvent(new CustomEvent("event-created"));
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
        aria-label="Criar evento"
      >
        <CalendarPlus className="h-6 w-6" />
      </button>

      {open && (
        <CreateEventModal
          open={open}
          onClose={() => setOpen(false)}
          onSubmit={handleSubmit}
        />
      )}
    </>
  );
}
