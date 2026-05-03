"use client";

import { useState, useRef, useEffect } from "react";
import { CalendarDays, MapPin, Type, FileText, X, Sparkles } from "lucide-react";

interface CreateEventModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    description: string;
    event_date: string;
    location: string;
    category?: string;
  }) => Promise<boolean> | boolean;
}

const CATEGORIES = [
  { value: "festa", label: "Festa" },
  { value: "palestra", label: "Palestra" },
  { value: "esporte", label: "Esporte" },
  { value: "cultura", label: "Cultura" },
  { value: "outro", label: "Outro" },
];

export default function CreateEventModal({ open, onClose, onSubmit }: CreateEventModalProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("festa");
  const [sending, setSending] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);

  // Foco automático no título ao abrir
  useEffect(() => {
    if (open) {
      // Pequeno delay para a animação do modal
      setTimeout(() => titleRef.current?.focus(), 100);
    }
  }, [open]);

  function reset() {
    setTitle("");
    setDescription("");
    setEventDate("");
    setLocation("");
    setCategory("festa");
    setSending(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleSubmit() {
    if (!title.trim() || !description.trim() || !eventDate || !location.trim() || sending) return;
    setSending(true);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim(),
        event_date: eventDate,
        location: location.trim(),
        category,
      });
      handleClose();
    } catch (err: unknown) {
      const detail = (err as any)?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: any) => d.msg || d.message).join("; ")
        : detail || (err as any)?.message || "Erro desconhecido ao criar evento.";
      alert(msg);
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-end justify-center bg-black/80 backdrop-blur-sm md:items-center md:p-8"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div
        className="flex w-full max-w-lg flex-col rounded-t-2xl border border-zinc-800/60 bg-zinc-950 shadow-2xl md:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ──────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-zinc-800/60 px-4 py-3">
          <button
            onClick={handleClose}
            className="rounded-full p-2 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
          >
            <X className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-zinc-100">Criar Evento</span>
          <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-emerald-400/80">
            <Sparkles className="h-3 w-3" />
            Novo
          </div>
        </div>

        {/* ── Body ────────────────────────────────────────── */}
        <div className="flex flex-col gap-5 px-4 py-6">
          {/* Título */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <Type className="h-3.5 w-3.5 text-violet-400" />
              Título do evento
            </label>
            <input
              ref={titleRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Festa de Recepção dos Calouros"
              maxLength={120}
              className="w-full rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-4 py-3 text-sm font-semibold text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  document.getElementById("event-desc-input")?.focus();
                }
              }}
            />
          </div>

          {/* Data */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <CalendarDays className="h-3.5 w-3.5 text-emerald-400" />
              Data do evento
            </label>
            <input
              type="datetime-local"
              value={eventDate}
              onChange={(e) => setEventDate(e.target.value)}
              className="w-full rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-100 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 [color-scheme:dark]"
            />
          </div>

          {/* Local */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <MapPin className="h-3.5 w-3.5 text-violet-400" />
              Local
            </label>
            <input
              type="text"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Ex: Auditório Central, Bloco A"
              maxLength={200}
              className="w-full rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  document.getElementById("event-category-select")?.focus();
                }
              }}
            />
          </div>

          {/* Categoria */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              Categoria
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  id={cat.value === category ? "event-category-select" : undefined}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
                    category === cat.value
                      ? "bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/40"
                      : "bg-zinc-800 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Descrição */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <FileText className="h-3.5 w-3.5 text-violet-400" />
              Descrição
            </label>
            <textarea
              id="event-desc-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Descreva o evento, programação, como participar..."
              rows={4}
              maxLength={2000}
              className="w-full resize-none rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 text-sm leading-relaxed text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
            />
          </div>
        </div>

        {/* ── Footer ──────────────────────────────────────── */}
        <div className="flex items-center justify-end gap-3 border-t border-zinc-800/60 px-4 py-4">
          <button
            onClick={handleClose}
            className="rounded-full px-5 py-2.5 text-sm font-semibold text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !description.trim() || !eventDate || !location.trim() || sending}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-600 to-emerald-500 px-6 py-2.5 text-sm font-bold text-white shadow-lg transition-all hover:from-violet-500 hover:to-emerald-400 disabled:cursor-not-allowed disabled:opacity-40 active:scale-95"
          >
            {sending ? (
              "Criando..."
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Criar Evento
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
