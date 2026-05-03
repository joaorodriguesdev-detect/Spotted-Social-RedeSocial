"use client";

import { usePathname } from "next/navigation";
import FeedFAB from "@/components/FeedFAB";
import EventFAB from "@/components/EventFAB";
import MuralFAB from "@/components/MuralFAB";

/**
 * FloatingButton – Dispatcher ESTRITO de botões flutuantes.
 *
 * Cada rota tem seu próprio componente especializado:
 *   - / ou /feed  →  FeedFAB   (CreatePostModal)
 *   - /eventos     →  EventFAB  (CreateEventModal)
 *   - /mural       →  MuralFAB  (CreateMuralModal)
 *   - qualquer outra rota → null (nada é renderizado)
 *
 * Isso GARANTE que:
 *   - Em /eventos, o CreatePostModal NUNCA é instanciado.
 *   - Em /mural, o CreateEventModal NUNCA é instanciado.
 *   - Não há estado compartilhado entre os botões.
 */
export default function FloatingButton() {
  const pathname = usePathname();

  if (pathname === "/" || pathname.startsWith("/feed")) {
    return <FeedFAB />;
  }

  if (pathname.startsWith("/eventos")) {
    return <EventFAB />;
  }

  if (pathname.startsWith("/mural")) {
    return <MuralFAB />;
  }

  // Qualquer outra rota (dm, perfil, direct, admin, notificacoes, etc.): sem FAB
  return null;
}
