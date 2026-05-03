"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Bell } from "lucide-react";
import Link from "next/link";

// ── Types ──────────────────────────────────────────────────────────────
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

// ── Helpers ────────────────────────────────────────────────────────────
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
      return "👤";
    case "mural":
      return "📋";
    case "like":
      return "❤️";
    case "comment":
      return "💬";
    default:
      return "🔔";
  }
}

// ── Component ──────────────────────────────────────────────────────────
export default function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // ── Fetch unread count (polling) ────────────────────────────────────
  const fetchUnreadCount = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/unread-count`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.unread_count);
      }
    } catch {
      // silencioso
    }
  }, []);

  // Polling a cada 30s
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  // ── Fetch full list when opening dropdown ───────────────────────────
  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/notifications/?skip=0&limit=15`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data: NotifResponse = await res.json();
        setNotifications(data.items);
        setUnreadCount(data.unread_count);
      }
    } catch {
      // silencioso
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Open / Close dropdown ───────────────────────────────────────────
  const toggleDropdown = () => {
    const next = !open;
    setOpen(next);
    if (next) {
      fetchNotifications();
    }
  };

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  // ── Mark as read ────────────────────────────────────────────────────
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
    } catch {
      // silencioso
    }
  };

  // ── Mark all as read ────────────────────────────────────────────────
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
    } catch {
      // silencioso
    }
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={toggleDropdown}
        className="relative p-2 rounded-full text-gray-400 hover:text-purple-400 hover:bg-gray-800/50 transition-all"
        aria-label="Notificações"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold text-white bg-red-500 rounded-full shadow-lg shadow-red-500/30 animate-glow-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-gray-900 border border-purple-900/40 rounded-xl shadow-2xl shadow-purple-900/20 overflow-hidden z-50">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-purple-900/30">
            <h3 className="text-sm font-semibold text-gray-200">
              Notificações
            </h3>
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
              >
                Marcar todas como lidas
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">
                <p>Nenhuma notificação</p>
              </div>
            ) : (
              <div className="divide-y divide-purple-900/20">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className={`flex items-start gap-3 px-4 py-3 transition-colors hover:bg-gray-800/40 cursor-pointer ${
                      !notif.is_read ? "bg-purple-900/10" : ""
                    }`}
                    onClick={() => {
                      if (!notif.is_read) markAsRead(notif.id);
                    }}
                  >
                    {/* Icon */}
                    <span className="text-base mt-0.5 shrink-0">
                      {getIcon(notif.category)}
                    </span>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-300">
                        <span className="font-medium text-gray-100">
                          {notif.sender_name || "Alguém"}
                        </span>{" "}
                        {notif.action_type}
                      </p>
                      <p className="text-xs text-gray-600 mt-0.5">
                        {timeAgo(notif.timestamp)}
                      </p>
                    </div>

                    {/* Unread dot */}
                    {!notif.is_read && (
                      <span className="w-2 h-2 rounded-full bg-purple-500 shrink-0 mt-2" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <Link
            href="/notificacoes"
            className="block text-center text-xs text-purple-400 hover:text-purple-300 py-3 border-t border-purple-900/30 transition-colors"
            onClick={() => setOpen(false)}
          >
            Ver todas as notificações →
          </Link>
        </div>
      )}
    </div>
  );
}
