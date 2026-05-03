"use client";

import { useState, useRef, useEffect } from "react";
import { ClipboardList, FileText, Tag, X, Sparkles, Contact } from "lucide-react";

interface CreateMuralModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    content: string;
    category: string;
    contact_info: string;
  }) => Promise<boolean> | boolean;
}

const CATEGORIES = [
  { value: "geral", label: "Geral" },
  { value: "achados", label: "Achados & Perdidos" },
  { value: "evento", label: "Evento" },
  { value: "serviço", label: "Serviço" },
];

export default function CreateMuralModal({ open, onClose, onSubmit }: CreateMuralModalProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("geral");
  const [contactInfo, setContactInfo] = useState("");
  const [sending, setSending] = useState(false);

  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => titleRef.current?.focus(), 100);
    }
  }, [open]);

  function reset() {
    setTitle("");
    setContent("");
    setCategory("geral");
    setContactInfo("");
    setSending(false);
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleSubmit() {
    if (!title.trim() || !content.trim() || sending) return;
    setSending(true);
    try {
      await onSubmit({
        title: title.trim(),
        content: content.trim(),
        category,
        contact_info: contactInfo.trim(),
      });
      handleClose();
    } catch (err: unknown) {
      const detail = (err as any)?.response?.data?.detail;
      const msg = Array.isArray(detail)
        ? detail.map((d: any) => d.msg || d.message).join("; ")
        : detail || (err as any)?.message || "Erro desconhecido ao publicar no mural.";
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
          <span className="text-sm font-semibold text-zinc-100">Publicar no Mural</span>
          <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-400/80">
            <Sparkles className="h-3 w-3" />
            Aviso
          </div>
        </div>

        {/* ── Body ────────────────────────────────────────── */}
        <div className="flex flex-col gap-5 px-4 py-6">
          {/* Categoria */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <Tag className="h-3.5 w-3.5 text-amber-400" />
              Categoria
            </label>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => setCategory(cat.value)}
                  className={`rounded-full px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
                    category === cat.value
                      ? "bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/40"
                      : "bg-zinc-800 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Título */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <FileText className="h-3.5 w-3.5 text-violet-400" />
              Título do anúncio
            </label>
            <input
              ref={titleRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Ex: Bicicleta perdida no Bloco II"
              maxLength={120}
              className="w-full rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-4 py-3 text-sm font-semibold text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  document.getElementById("mural-content-input")?.focus();
                }
              }}
            />
          </div>

          {/* Descrição */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <ClipboardList className="h-3.5 w-3.5 text-emerald-400" />
              Descrição
            </label>
            <textarea
              id="mural-content-input"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Descreva seu anúncio, aviso ou serviço..."
              rows={4}
              maxLength={2000}
              className="w-full resize-none rounded-xl border border-zinc-800/60 bg-zinc-900/50 p-4 text-sm leading-relaxed text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
            />
          </div>

          {/* Informações de contato */}
          <div>
            <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-zinc-400">
              <Contact className="h-3.5 w-3.5 text-amber-400" />
              Contato <span className="font-normal text-zinc-600">(opcional)</span>
            </label>
            <input
              type="text"
              value={contactInfo}
              onChange={(e) => setContactInfo(e.target.value)}
              placeholder="Instagram, WhatsApp, e-mail..."
              maxLength={200}
              className="w-full rounded-xl border border-zinc-800/60 bg-zinc-900/50 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-600 outline-none transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
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
            disabled={!title.trim() || !content.trim() || sending}
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-amber-500 to-emerald-500 px-6 py-2.5 text-sm font-bold text-white shadow-lg transition-all hover:from-amber-400 hover:to-emerald-400 disabled:cursor-not-allowed disabled:opacity-40 active:scale-95"
          >
            {sending ? (
              "Publicando..."
            ) : (
              <>
                <ClipboardList className="h-4 w-4" />
                Publicar no Mural
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
