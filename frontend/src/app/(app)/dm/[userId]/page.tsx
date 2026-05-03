"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, Send } from "lucide-react";

// ── Mock: usuários ────────────────────────────────────────────────────
const MOCK_USERS: Record<number, { name: string; username: string; online: boolean }> = {
  1: { name: "Marina Lopes", username: "marina.l", online: true },
  2: { name: "Rafael Oliveira", username: "rafa.oli", online: false },
  3: { name: "Camila Torres", username: "camila.t", online: true },
  4: { name: "Prof. Ricardo", username: "prof.ricardo", online: false },
  5: { name: "Beatriz Nunes", username: "bia.nunes", online: true },
  6: { name: "Lucas Mendes", username: "lucas.m", online: false },
};

// ── Mock: mensagens ───────────────────────────────────────────────────
function buildMockMessages(userId: number) {
  const base = [
    { id: 1, fromMe: false, text: "Oiee! Tudo bem? 😊", time: "10:30" },
    { id: 2, fromMe: true, text: "Oi! Tudo sim, e vc?", time: "10:32" },
    { id: 3, fromMe: false, text: "Tudo ótimo! Vi que vc tbm faz CC, que massa!", time: "10:33" },
    { id: 4, fromMe: true, text: "Sim! Tô no 4º período. E vc?", time: "10:35" },
    { id: 5, fromMe: false, text: "3º período ainda 😅", time: "10:36" },
    { id: 6, fromMe: true, text: "Boa! Qual matéria tá mais pesada?", time: "10:38" },
    { id: 7, fromMe: false, text: "Estrutura de Dados tô sofrendo kk", time: "10:39" },
    { id: 8, fromMe: true, text: "Relaxa, depois do 4º período melhora! Bora trocar umas ideias sobre os projetos", time: "10:40" },
    { id: 9, fromMe: false, text: "Bora sim! 🚀", time: "10:41" },
  ];
  return base.map((m) => ({
    ...m,
    text:
      userId === 2
        ? m.fromMe ? m.text : ["Beleza, então fechado!", "Pode deixar que eu resolvo.", "Valeu mesmo!", "Tô chegando já!", "Nos vemos lá!"][m.id % 5]
        : userId === 3
          ? m.fromMe ? m.text : ["Você vai na palestra de hoje?", "Vai ser sobre IA, super interessante!", "Vamos juntos?", "Te encontro lá às 17h!", "Bora!"][m.id % 5]
          : m.text,
  }));
}

function getInitials(name: string): string {
  return name.split(" ")[0][0].toUpperCase();
}

export default function ChatPage() {
  const router = useRouter();
  const params = useParams();
  const userId = Number(params.userId);
  const userData = MOCK_USERS[userId];

  const [messages] = useState(() => buildMockMessages(userId));
  const [input, setInput] = useState("");

  if (!userData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-zinc-500">
        <p>Usuário não encontrado.</p>
      </div>
    );
  }

  return (
    <div className="flex h-dvh flex-col bg-black">
      {/* ── Header fixo ─────────────────────────────────────────── */}
      <header className="flex items-center gap-3 border-b border-zinc-800/60 bg-black/90 px-4 py-3 backdrop-blur-xl">
        <button
          onClick={() => router.back()}
          className="rounded-full p-2 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="relative shrink-0">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400/30 to-violet-500/30 text-sm font-bold text-violet-400">
              {getInitials(userData.name)}
            </div>
            {userData.online && (
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-black bg-emerald-500" />
            )}
          </div>
          <div>
            <p className="text-sm font-bold text-zinc-100">{userData.name}</p>
            <p className="text-xs text-zinc-500">
              {userData.online ? "Online" : "Offline"}
            </p>
          </div>
        </div>
      </header>

      {/* ── Mensagens ───────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        <div className="mx-auto max-w-2xl space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.fromMe ? "justify-end" : "justify-start"}`}
            >
              {!msg.fromMe && (
                <div className="mr-2 mt-auto flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-[10px] font-bold text-zinc-400">
                  {getInitials(userData.name)}
                </div>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.fromMe
                    ? "bg-gradient-to-r from-violet-600 to-emerald-500 text-white"
                    : "bg-zinc-800 text-zinc-200"
                }`}
              >
                <p>{msg.text}</p>
                <p
                  className={`mt-1 text-right text-[10px] ${
                    msg.fromMe ? "text-white/60" : "text-zinc-500"
                  }`}
                >
                  {msg.time}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Input fixo no rodapé ──────────────────────────────────── */}
      <div className="border-t border-zinc-800/60 bg-black px-4 py-3">
        <div className="mx-auto flex max-w-2xl items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Mensagem não criptografada"
            className="flex-1 rounded-full border border-zinc-800/60 bg-zinc-900/50 px-5 py-2.5 text-sm text-zinc-100 outline-none placeholder-zinc-500 transition-colors focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
            onKeyDown={(e) => {
              if (e.key === "Enter" && input.trim()) {
                console.log("Enviar:", input);
                setInput("");
              }
            }}
          />
          <button
            onClick={() => {
              if (input.trim()) {
                console.log("Enviar:", input);
                setInput("");
              }
            }}
            disabled={!input.trim()}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-violet-600 to-emerald-500 text-white transition-all hover:scale-105 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
