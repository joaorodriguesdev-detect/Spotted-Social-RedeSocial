"use client";

import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { CalendarDays, Clock3, Loader2, MapPin, Sparkles } from "lucide-react";
import apiClient, { extractErrorMessage } from "@/lib/api-client";
import type { Event, EventListResponse } from "@/types";
import SectionTabs from "@/components/SectionTabs";

function EventSkeletonCard() {
  return (
    <article className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-zinc-950/60">
      <div className="h-40 animate-pulse bg-zinc-900/80" />
      <div className="space-y-3 p-5 animate-pulse">
        <div className="h-4 w-24 rounded-full bg-zinc-800" />
        <div className="h-5 w-3/4 rounded-full bg-zinc-800" />
        <div className="h-3 w-full rounded-full bg-zinc-800/80" />
        <div className="h-3 w-5/6 rounded-full bg-zinc-800/80" />
        <div className="flex gap-2 pt-2">
          <div className="h-9 w-28 rounded-full bg-zinc-800" />
          <div className="h-9 w-24 rounded-full bg-zinc-800" />
        </div>
      </div>
    </article>
  );
}

function timeUntil(dateIso: string): string {
  const diff = new Date(dateIso).getTime() - Date.now();
  const days = Math.round(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return "Hoje";
  if (days > 0) return "Em " + days + " dia(s)";
  return "Ha " + Math.abs(days) + " dia(s)";
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function EventosPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const fetchEvents = useCallback(async (nextPage = 1) => {
    setLoading(true);
    setError("");
    try {
      const response = await apiClient.get<EventListResponse>("/api/events/", {
        params: { page: nextPage, per_page: 12 },
      });

      setEvents((prev) => (nextPage === 1 ? response.data.items : [...prev, ...response.data.items]));
      setPage(response.data.page);
      setHasMore(response.data.page < response.data.total_pages);
    } catch (err) {
      console.error("[Eventos.fetchEvents] erro ao carregar eventos:", err);
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEvents(1);
  }, [fetchEvents]);

  // Recarrega a lista quando um evento for criado
  useEffect(() => {
    function handleEventCreated() {
      fetchEvents(1);
    }
    window.addEventListener("event-created", handleEventCreated);
    return () => window.removeEventListener("event-created", handleEventCreated);
  }, [fetchEvents]);

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      fetchEvents(page + 1);
    }
  };

  return (
    <main className="min-h-screen bg-black text-zinc-100 pb-28">
      <SectionTabs />
      <div className="mx-auto max-w-4xl px-4 py-6 space-y-6 min-h-[calc(100vh-12rem)]">

        <header className="rounded-[1.75rem] border border-white/10 bg-zinc-950/70 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300/80">
                Eventos
              </p>
              <h1 className="mt-2 text-2xl font-bold text-zinc-50 sm:text-3xl">
                Descubra encontros, palestras e roles da comunidade.
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-zinc-400">
                Uma vitrine elegante de eventos futuros com a identidade Dark Premium do Spotted.
              </p>
            </div>
            <div className="inline-flex items-center gap-2 self-start rounded-full border border-violet-500/20 bg-violet-500/10 px-4 py-2 text-xs font-semibold text-violet-300 sm:self-auto">
              <Sparkles className="h-4 w-4" />
              Proximos eventos
            </div>
          </div>
        </header>

        {error ? (
          <div className="rounded-[1.5rem] border border-red-500/20 bg-red-950/30 p-5 text-sm text-red-300">
            <p className="font-semibold">Nao foi possivel carregar os eventos.</p>
            <p className="mt-1 text-red-200/80">{error}</p>
            <button
              type="button"
              onClick={() => fetchEvents(1)}
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-red-500/15 px-4 py-2 font-semibold text-red-200 transition-colors hover:bg-red-500/25"
            >
              <Loader2 className="h-4 w-4" />
              Tentar novamente
            </button>
          </div>
        ) : null}

        {loading && events.length === 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <EventSkeletonCard />
            <EventSkeletonCard />
            <EventSkeletonCard />
            <EventSkeletonCard />
          </div>
        ) : events.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {events.map((event) => (
              <article
                key={event.id}
                className="group overflow-hidden rounded-[1.5rem] border border-white/10 bg-zinc-950/65 shadow-[0_18px_50px_rgba(0,0,0,0.35)] transition-all hover:border-violet-500/30 hover:bg-zinc-900/70"
              >
                <div className="relative h-40 w-full bg-gradient-to-br from-emerald-500/20 via-violet-500/20 to-black">
                  {event.media_url ? (
                    <Image
                      src={`${API_BASE}/static/uploads/${event.media_url}`}
                      alt={event.title}
                      fill
                      className="object-cover opacity-90"
                      unoptimized
                    />
                  ) : null}
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent" />
                  <div className="absolute left-4 top-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/50 px-3 py-1 text-xs font-semibold text-zinc-100 backdrop-blur-md">
                    <CalendarDays className="h-3.5 w-3.5 text-emerald-300" />
                    {timeUntil(event.event_date)}
                  </div>
                </div>

                <div className="space-y-3 p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold text-zinc-50">
                        {event.title}
                      </h2>
                      <p className="text-xs text-violet-300/80">
                        {event.creator_name || event.creator_username || "Spotted"}
                      </p>
                    </div>
                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-300">
                      Evento
                    </span>
                  </div>

                  <p className="line-clamp-3 text-sm leading-6 text-zinc-300">
                    {event.description}
                  </p>

                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <MapPin className="h-4 w-4 text-violet-300" />
                    <span className="truncate">{event.location}</span>
                  </div>

                  <div className="flex items-center gap-2 text-sm text-zinc-400">
                    <Clock3 className="h-4 w-4 text-emerald-300" />
                    <span>{new Date(event.event_date).toLocaleDateString("pt-BR")}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-[1.5rem] border border-white/10 bg-zinc-950/60 p-8 text-center text-sm text-zinc-400">
            Nenhum evento encontrado no momento.
          </div>
        )}

        {hasMore ? (
          <div className="flex justify-center pt-2">
            <button
              type="button"
              onClick={handleLoadMore}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-full border border-violet-500/20 bg-violet-600 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_32px_rgba(124,58,237,0.24)] transition-all hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Carregando...
                </>
              ) : (
                "Carregar mais"
              )}
            </button>
          </div>
        ) : null}
      </div>

    </main>
  );
}
