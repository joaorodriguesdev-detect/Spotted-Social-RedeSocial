"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import CreatePostModal from "@/components/CreatePostModal";

/**
 * FeedFAB – Botão flutuante EXCLUSIVO do Feed.
 *
 * REGRA ESTRITA:
 *   - Só renderiza se pathname === "/" ou pathname.startsWith("/feed").
 *   - Só abre o CreatePostModal.
 *   - NUNCA importa CreateEventModal nem CreateMuralModal.
 */
export default function FeedFAB() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [open, setOpen] = useState(false);

  // ── Validação de rota: só renderiza no Feed ───────────────
  if (pathname !== "/" && !pathname.startsWith("/feed")) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-24 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-r from-violet-600 to-emerald-500 text-white shadow-[0_8px_32px_rgba(124,58,237,0.35)] transition-all hover:scale-110 hover:shadow-[0_12px_40px_rgba(124,58,237,0.45)] active:scale-95"
        aria-label="Criar spot"
      >
        <Plus className="h-6 w-6" />
      </button>

      {open && (
        <CreatePostModal
          user={
            user
              ? {
                  id: user.id,
                  username: user.username,
                  name: user.name,
                  profile_pic: user.profile_pic,
                }
              : null
          }
          open={open}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
