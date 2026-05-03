"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, Bell, CheckCheck } from "lucide-react";
import Link from "next/link";

// â”€â”€ Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface NotificationItem {
  id: number;
  user_id: number;
  sender_name: string | null;
  action_type: string | null;
  category: string;
  post_id: number | null;
  is_read: boolean;
  timestamp: string | null;
}

interface NotifResponse {
  items: NotificationItem[];
  unread_count: number;
  total: number;
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

function getIcon(category: string): string {
  switch (category) {
    case "follow":
      return "ðŸ‘¤";
    case "mural":
      return "ðŸ“‹";
    case "like":
      return "â¤ï¸";
    case "comment":
      return "ðŸ’¬";
    default:
      return "ðŸ””";
  }
}

export default function NotificacoesPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [unreadCount, setUnreadCount] = useState(0);
  const [total, setTotal] = useState(0);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/notifications/?skip=0&limit=100`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data: NotifResponse = await res.json();
        setNotifications(data.items);
        setUnreadCount(data.unread_count);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("[Notificacoes.fetchAll] erro ao carregar notificaÃ§Ãµes:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // â”€â”€ Mark as read â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const markAsRead = async (notifId: number) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/notifications/${notifId}/read`,
        { method: "PATCH", credentials: "include" }
      );
      if (res.ok) {
        setNotifications((prev) =>
          prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error("[Notificacoes.markAsRead] erro ao marcar notificaÃ§Ã£o:", err);
    }
  };

  const markAllAsRead = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/read-all`, {
        method: "PATCH",
        credentials: "include",
      });
      if (res.ok) {
        setNotifications((prev) =>
          prev.map((n) => ({ ...n, is_read: true }))
        );
        setUnreadCount(0);
      }
    } catch (err) {
      console.error("[Notificacoes.markAllAsRead] erro ao marcar todas:", err);
    }
  };

  // â”€â”€ Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  if (loading) {
    return (
      <div className="min-h-screen bg-black text-zinc-100">
<div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-10 h-10 animate-spin text-violet-400" />
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-black pb-28 text-zinc-100">
<div className="mx-auto max-w-2xl px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 flex items-center gap-2">
            <Bell className="w-6 h-6 text-violet-400" />
            NotificaÃ§Ãµes
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            {unreadCount > 0
              ? `${unreadCount} nÃ£o lida(s) de ${total} total`
              : "Todas lidas âœ“"}
          </p>
        </div>

        {unreadCount > 0 && (
          <button
            onClick={markAllAsRead}
            className="flex items-center gap-1.5 text-sm text-violet-400 hover:text-violet-300 transition-colors"
          >
            <CheckCheck className="w-4 h-4" />
            Marcar todas
          </button>
        )}
      </div>

      {/* List */}
      {notifications.length === 0 ? (
        <div className="text-center py-16">
          <Bell className="w-12 h-12 text-zinc-700 mx-auto mb-4" />
          <p className="text-zinc-500">Nenhuma notificaÃ§Ã£o ainda.</p>
          <p className="text-zinc-600 text-sm mt-1">
            Quando alguÃ©m interagir com vocÃª, aparecerÃ¡ aqui.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((notif) => (
            <div
              key={notif.id}
              className={`rounded-[1.5rem] border transition-all duration-300 p-4 ${
                notif.is_read
                  ? "border-white/10 bg-zinc-950/50"
                  : "border-violet-500/20 bg-violet-500/10 shadow-sm shadow-violet-500/10"
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <span className="text-xl mt-0.5 shrink-0">
                  {getIcon(notif.category)}
                </span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-zinc-300">
                    <span className="font-semibold text-zinc-50">
                      {notif.sender_name || "AlguÃ©m"}
                    </span>{" "}
                    {notif.action_type}
                  </p>
                  <p className="text-xs text-zinc-600 mt-0.5">
                    {timeAgo(notif.timestamp)}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  {!notif.is_read && (
                    <button
                      onClick={() => markAsRead(notif.id)}
                      className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                    >
                      Marcar lida
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Back link */}
      <div className="mt-8 text-center">
        <Link href="/" className="text-sm text-zinc-600 hover:text-violet-400 transition-colors">
          â† Voltar ao feed
        </Link>
      </div>
      </div>
    </main>
  );
}


