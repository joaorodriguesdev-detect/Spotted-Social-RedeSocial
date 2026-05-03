"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Loader2, Send, ArrowLeft, CheckCheck, Circle } from "lucide-react";
import Image from "next/image";
import apiClient from "@/lib/api-client";
import { useChat, type ChatMessageData } from "@/hooks/useChat";

// ── Types ──────────────────────────────────────────────────────────────
interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  media_url: string | null;
  created_at: string | null;
  all_read: boolean;
  is_mine: boolean;
}

interface OtherUser {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
}

interface ChatProps {
  otherUser: OtherUser;
  currentUserId: number;
  token: string;
  onBack?: () => void;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

function formatTime(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

// ── Component ──────────────────────────────────────────────────────────
export default function Chat({ otherUser, currentUserId, token, onBack }: ChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [online, setOnline] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── WebSocket hook ──────────────────────────────────────────────────
  const ws = useChat({
    token,
  });

  // ── Setup callbacks ──────────────────────────────────────────────────
  useEffect(() => {
    ws.onMessage((msg: ChatMessageData) => {
      setMessages((prev) => [...prev, msg]);
      scrollToBottom();
    });

    ws.onReadReceipt((data) => {
      setMessages((prev) =>
        prev.map((m) =>
          data.message_ids.includes(m.id) ? { ...m, all_read: true } : m
        )
      );
    });

    ws.onError((detail) => {
      console.error("WS Error:", detail);
    });
  }, [ws]);

  // ── Fetch history ───────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.get(`/api/chat/history/${otherUser.id}`);
      const data = res.data;
      setMessages(data.messages || []);
      setOnline(data.is_online);

      // Send read receipt for this conversation
      ws.sendReadReceipt(data.conversation_id);
    } catch (err) {
      console.error("Falha ao buscar histórico do chat:", err);
    } finally {
      setLoading(false);
    }
  }, [otherUser.id, ws]);

  useEffect(() => {
    if (otherUser.id) {
      fetchHistory();
    }
  }, [otherUser.id, fetchHistory]);

  // ── Scroll to bottom ────────────────────────────────────────────────
  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  };

  useEffect(() => {
    if (!loading) scrollToBottom();
  }, [messages, loading]);

  // ── Send message ────────────────────────────────────────────────────
  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setInput("");

    // Try WebSocket first
    const sent = ws.sendMessage(otherUser.id, text);
    if (sent) {
      // The message will appear via onNewMessage callback
      setSending(false);
      return;
    }

    // Fallback: REST API
    try {
      const res = await apiClient.post(`/api/chat/send/${otherUser.id}`, {
        content: text,
      });
      if (res.status === 200) {
        // Fetch history again to get the message with full data
        fetchHistory();
      }
    } catch (err) {
      console.error("Falha ao enviar mensagem via REST:", err);
    } finally {
      setSending(false);
    }
  };

  // ── Handle Enter key ────────────────────────────────────────────────
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Loading State ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full min-h-[80vh] max-h-[90vh]">
      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-purple-900/30 bg-gray-900/60 shrink-0">
        {onBack && (
          <button
            onClick={onBack}
            className="p-1 text-gray-400 hover:text-purple-400 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
        )}

        <div className="relative">
          {otherUser.profile_pic ? (
            <Image
              src={`${API_BASE}/static/uploads/${otherUser.profile_pic}`}
              alt={otherUser.username}
              width={40}
              height={40}
              className="w-10 h-10 rounded-full object-cover"
              unoptimized
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-sm font-bold text-black">
              {(otherUser.name || otherUser.username).charAt(0).toUpperCase()}
            </div>
          )}
          {online && (
            <span className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-500 rounded-full border-2 border-gray-950" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-200 truncate">
            {otherUser.name || otherUser.username}
          </p>
          <p className="text-xs text-gray-500">
            {online ? "Online" : "Offline"}
          </p>
        </div>
      </div>

      {/* ── Messages ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-600 text-sm">
            <p>Nenhuma mensagem ainda.</p>
            <p className="text-xs mt-1">Envie algo para começar!</p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.is_mine ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.is_mine
                    ? "bg-[#7b2cbf] text-white rounded-br-md"
                    : "bg-gray-800 text-gray-200 rounded-bl-md"
                }`}
              >
                <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                <div
                  className={`flex items-center gap-1 mt-1 ${
                    msg.is_mine ? "justify-end" : "justify-start"
                  }`}
                >
                  <span className="text-[10px] text-gray-400">
                    {formatTime(msg.created_at)}
                  </span>
                  {msg.is_mine && (
                    <CheckCheck
                      className={`w-3.5 h-3.5 ${
                        msg.all_read ? "text-emerald-400" : "text-gray-500"
                      }`}
                    />
                  )}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input ─────────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-purple-900/30 bg-gray-900/60 shrink-0">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Digite sua mensagem..."
            rows={1}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 resize-none max-h-32"
            style={{ minHeight: "42px" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="p-3 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all hover:from-purple-500 hover:to-pink-500 shrink-0"
          >
            {sending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
