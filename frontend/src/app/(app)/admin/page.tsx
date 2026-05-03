"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Loader2,
  Users,
  FileText,
  Tag,
  Activity,
  Shield,
  Ban,
  Trash2,
  CheckCircle,
  XCircle,
  Search,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";

// â”€â”€ Types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
interface StatsData {
  total_users: number;
  active_users: number;
  banned_users: number;
  online_users: number;
  new_users_today: number;
  total_posts: number;
  posts_today: number;
  active_coupons: number;
  total_coupons: number;
}

interface UserItem {
  id: number;
  username: string;
  name: string | null;
  university: string | null;
  bio: string | null;
  profile_pic: string | null;
  is_admin: boolean;
  is_verified: boolean;
  is_banned: boolean;
  created_at: string | null;
  posts_count: number;
  is_online: boolean;
}

interface LogItem {
  id: number;
  admin_id: number;
  admin_username: string | null;
  action: string;
  target_id: number | null;
  target_type: string;
  details: string | null;
  timestamp: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// â”€â”€ Helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    ban_user: "Banir usuÃ¡rio",
    unban_user: "Desbanir usuÃ¡rio",
    delete_post: "Deletar post",
    delete_mural: "Deletar anÃºncio",
    delete_coupon: "Remover cupom",
    approve_coupon: "Aprovar cupom",
  };
  return labels[action] || action;
}

function actionColor(action: string): string {
  if (action.includes("ban") || action.includes("delete")) return "text-red-400";
  if (action.includes("approve") || action.includes("unban")) return "text-emerald-400";
  return "text-gray-400";
}

type Tab = "stats" | "users" | "logs";

// â”€â”€ Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export default function AdminPage() {
  // Auth
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);

  // Tabs
  const [tab, setTab] = useState<Tab>("stats");

  // Data
  const [stats, setStats] = useState<StatsData | null>(null);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Users pagination
  const [userPage, setUserPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [userSearch, setUserSearch] = useState("");

  // Logs pagination
  const [logPage, setLogPage] = useState(1);
  const [logTotal, setLogTotal] = useState(0);

  // â”€â”€ Check if admin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          setIsAdmin(data.is_admin === true);
        } else {
          setIsAdmin(false);
        }
      } catch {
        setIsAdmin(false);
      }
    })();
  }, []);

  // â”€â”€ Fetch stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/stats`, {
        credentials: "include",
      });
      if (res.ok) {
        const data: StatsData = await res.json();
        setStats(data);
      }
    } catch {
      // silencioso
    }
  }, []);

  // â”€â”€ Fetch users â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const fetchUsers = useCallback(
    async (page = 1, search = "") => {
      try {
        const url = new URL(`${API_BASE}/api/admin/users`);
        url.searchParams.set("page", String(page));
        url.searchParams.set("per_page", "20");
        if (search) url.searchParams.set("search", search);

        const res = await fetch(url.toString(), { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          setUsers(data.items || []);
          setUserTotal(data.total || 0);
        }
      } catch {
        // silencioso
      }
    },
    []
  );

  // â”€â”€ Fetch logs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const fetchLogs = useCallback(async (page = 1) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/admin/logs?page=${page}&per_page=30`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setLogs(data.items || []);
        setLogTotal(data.total || 0);
      }
    } catch {
      // silencioso
    }
  }, []);

  // â”€â”€ Initial load â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    if (isAdmin === true) {
      setLoading(true);
      Promise.all([fetchStats(), fetchUsers(1, ""), fetchLogs(1)]).finally(() =>
        setLoading(false)
      );
    } else {
      setLoading(false);
    }
  }, [isAdmin, fetchStats, fetchUsers, fetchLogs]);

  // â”€â”€ Toggle ban â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const toggleBan = async (userId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/${userId}/ban`, {
        method: "PATCH",
        credentials: "include",
      });
      if (res.ok) {
        fetchUsers(userPage, userSearch);
        fetchStats();
        fetchLogs(logPage);
      }
    } catch {
      // silencioso
    }
  };

  // â”€â”€ Delete post â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const deletePost = async (postId: number) => {
    if (!confirm(`Deletar post #${postId}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/posts/${postId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (res.ok) {
        fetchStats();
        fetchLogs(logPage);
      }
    } catch {
      // silencioso
    }
  };

  // â”€â”€ Delete mural â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const deleteMural = async (muralId: number) => {
    if (!confirm(`Deletar anÃºncio #${muralId}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/mural/${muralId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (res.ok) {
        fetchStats();
        fetchLogs(logPage);
      }
    } catch {
      // silencioso
    }
  };

  // â”€â”€ Delete coupon â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const deleteCoupon = async (couponId: number) => {
    if (!confirm(`Remover cupom #${couponId}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/api/admin/coupons/${couponId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (res.ok) {
        fetchStats();
        fetchLogs(logPage);
      }
    } catch {
      // silencioso
    }
  };

  // â”€â”€ Approve coupon â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const approveCoupon = async (couponId: number) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/admin/coupons/${couponId}/approve`,
        { method: "PATCH", credentials: "include" }
      );
      if (res.ok) {
        fetchStats();
        fetchLogs(logPage);
      }
    } catch {
      // silencioso
    }
  };

  // â”€â”€ Access denied â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  if (isAdmin === false) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <div className="bg-red-950/40 border border-red-800/40 rounded-xl p-8 text-center max-w-md">
          <Shield className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 text-lg font-medium mb-2">
            Acesso negado
          </p>
          <p className="text-gray-500 text-sm">
            Apenas administradores podem acessar esta pÃ¡gina.
          </p>
          <Link
            href="/"
            className="inline-block mt-4 text-sm text-gray-500 hover:text-purple-400 transition-colors"
          >
            â† Voltar ao feed
          </Link>
        </div>
      </div>
    );
  }

  // â”€â”€ Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  if (loading || isAdmin === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-950">
        <Loader2 className="w-10 h-10 animate-spin text-purple-400" />
      </div>
    );
  }

  // â”€â”€ Tabs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "stats", label: "Dashboard", icon: <Activity className="w-4 h-4" /> },
    { key: "users", label: "UsuÃ¡rios", icon: <Users className="w-4 h-4" /> },
    { key: "logs", label: "Auditoria", icon: <Shield className="w-4 h-4" /> },
  ];

  // â”€â”€ Render â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 pb-16">
<nav className="sticky top-0 z-50 border-b border-red-900/30 bg-gray-950/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-red-400" />
            <span className="text-lg font-bold text-red-400">Painel Admin</span>
          </div>
          <Link
            href="/"
            className="text-sm text-gray-500 hover:text-purple-400 transition-colors"
          >
            â† Sair
          </Link>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* â”€â”€ Tabs â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */}
        <div className="flex items-center gap-2 mb-8 border-b border-gray-800 pb-2">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-t-lg text-sm font-medium transition-all ${
                tab === t.key
                  ? "bg-red-900/30 text-red-400 border-b-2 border-red-500"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>

        {/* â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
            â•‘  TAB 1 â€“ DASHBOARD STATS                                 â•‘
            â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
        {tab === "stats" && (
          <div>
            {stats && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Card: UsuÃ¡rios */}
                <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-blue-900/40">
                      <Users className="w-5 h-5 text-blue-400" />
                    </div>
                    <p className="text-sm text-gray-400 font-medium">UsuÃ¡rios</p>
                  </div>
                  <p className="text-3xl font-bold text-white">{stats.total_users}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span className="text-emerald-400">{stats.active_users} ativos</span>
                    <span className="text-red-400">{stats.banned_users} banidos</span>
                    <span className="text-cyan-400">{stats.online_users} online</span>
                  </div>
                </div>

                {/* Card: Posts */}
                <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-purple-900/40">
                      <FileText className="w-5 h-5 text-purple-400" />
                    </div>
                    <p className="text-sm text-gray-400 font-medium">Posts</p>
                  </div>
                  <p className="text-3xl font-bold text-white">{stats.total_posts}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    {stats.posts_today} nas Ãºltimas 24h
                  </p>
                </div>

                {/* Card: Cupons */}
                <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-pink-900/40">
                      <Tag className="w-5 h-5 text-pink-400" />
                    </div>
                    <p className="text-sm text-gray-400 font-medium">Cupons</p>
                  </div>
                  <p className="text-3xl font-bold text-white">{stats.total_coupons}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    {stats.active_coupons} ativos
                  </p>
                </div>

                {/* Card: Novos hoje */}
                <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="p-2 rounded-lg bg-emerald-900/40">
                      <Activity className="w-5 h-5 text-emerald-400" />
                    </div>
                    <p className="text-sm text-gray-400 font-medium">Novos hoje</p>
                  </div>
                  <p className="text-3xl font-bold text-white">{stats.new_users_today}</p>
                  <p className="text-xs text-gray-500 mt-2">
                    usuÃ¡rios cadastrados nas Ãºltimas 24h
                  </p>
                </div>
              </div>
            )}

            {/* Quick actions */}
            <div className="mt-8">
              <h2 className="text-lg font-semibold text-gray-200 mb-4">
                AÃ§Ãµes RÃ¡pidas
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <button
                  onClick={() => setTab("users")}
                  className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-left hover:border-red-500/40 transition-all"
                >
                  <p className="text-sm font-medium text-gray-200">Gerenciar UsuÃ¡rios</p>
                  <p className="text-xs text-gray-500 mt-1">Banir / desbanir contas</p>
                </button>
                <button
                  onClick={() => setTab("logs")}
                  className="rounded-xl border border-gray-800 bg-gray-900/60 p-4 text-left hover:border-red-500/40 transition-all"
                >
                  <p className="text-sm font-medium text-gray-200">Ver Logs</p>
                  <p className="text-xs text-gray-500 mt-1">Auditar aÃ§Ãµes dos admins</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
            â•‘  TAB 2 â€“ USERS TABLE                                    â•‘
            â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
        {tab === "users" && (
          <div>
            {/* Search */}
            <div className="flex items-center gap-3 mb-4">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  value={userSearch}
                  onChange={(e) => {
                    setUserSearch(e.target.value);
                    setUserPage(1);
                  }}
                  placeholder="Buscar usuÃ¡rioâ€¦"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-red-500/50"
                />
              </div>
              <button
                onClick={() => fetchUsers(userPage, userSearch)}
                className="px-3 py-2 rounded-lg bg-gray-800 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
              >
                Buscar
              </button>
              <span className="text-sm text-gray-500">
                {userTotal} usuÃ¡rio(s)
              </span>
            </div>

            {/* Table */}
            <div className="overflow-x-auto rounded-xl border border-gray-800">
              <table className="w-full text-sm">
                <thead className="bg-gray-900 text-gray-400">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">UsuÃ¡rio</th>
                    <th className="text-left px-4 py-3 font-medium">Status</th>
                    <th className="text-left px-4 py-3 font-medium">Posts</th>
                    <th className="text-left px-4 py-3 font-medium">Criado em</th>
                    <th className="text-right px-4 py-3 font-medium">AÃ§Ãµes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {users.map((u) => (
                    <tr
                      key={u.id}
                      className={`hover:bg-gray-800/40 transition-colors ${
                        u.is_banned ? "opacity-60" : ""
                      }`}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {u.profile_pic ? (
                            <Image
                              src={`${API_BASE}/static/uploads/${u.profile_pic}`}
                              alt={u.username}
                              width={36}
                              height={36}
                              className="w-9 h-9 rounded-full object-cover"
                              unoptimized
                            />
                          ) : (
                            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-xs font-bold text-black">
                              {(u.name || u.username).charAt(0).toUpperCase()}
                            </div>
                          )}
                          <div>
                            <p className="text-gray-200 font-medium">
                              {u.name || u.username}
                              {u.is_admin && (
                                <span className="ml-2 text-[10px] text-red-400 font-semibold">
                                  ADMIN
                                </span>
                              )}
                              {u.is_verified && (
                                <span className="ml-1 text-[10px] text-cyan-400">
                                  âœ“
                                </span>
                              )}
                            </p>
                            <p className="text-xs text-gray-500">@{u.username}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {u.is_online && (
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                          )}
                          <span
                            className={`text-xs ${
                              u.is_banned
                                ? "text-red-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {u.is_banned ? "Banido" : u.is_online ? "Online" : "Offline"}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-400">{u.posts_count}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">
                        {timeAgo(u.created_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => toggleBan(u.id)}
                          className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            u.is_banned
                              ? "bg-emerald-900/40 text-emerald-400 hover:bg-emerald-800/40"
                              : "bg-red-900/40 text-red-400 hover:bg-red-800/40"
                          }`}
                        >
                          <Ban className="w-3 h-3" />
                          {u.is_banned ? "Desbanir" : "Banir"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {userTotal > 20 && (
              <div className="flex items-center justify-center gap-4 mt-4">
                <button
                  onClick={() => {
                    const p = Math.max(1, userPage - 1);
                    setUserPage(p);
                    fetchUsers(p, userSearch);
                  }}
                  disabled={userPage <= 1}
                  className="p-2 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-gray-500">
                  PÃ¡gina {userPage} de {Math.ceil(userTotal / 20)}
                </span>
                <button
                  onClick={() => {
                    const p = userPage + 1;
                    setUserPage(p);
                    fetchUsers(p, userSearch);
                  }}
                  disabled={userPage >= Math.ceil(userTotal / 20)}
                  className="p-2 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
            â•‘  TAB 3 â€“ AUDIT LOGS                                    â•‘
            â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */}
        {tab === "logs" && (
          <div>
            <p className="text-sm text-gray-500 mb-4">
              Registro de todas as aÃ§Ãµes de moderaÃ§Ã£o realizadas por administradores.
            </p>

            <div className="overflow-x-auto rounded-xl border border-gray-800">
              <table className="w-full text-sm">
                <thead className="bg-gray-900 text-gray-400">
                  <tr>
                    <th className="text-left px-4 py-3 font-medium">Admin</th>
                    <th className="text-left px-4 py-3 font-medium">AÃ§Ã£o</th>
                    <th className="text-left px-4 py-3 font-medium">Alvo</th>
                    <th className="text-left px-4 py-3 font-medium">Detalhes</th>
                    <th className="text-left px-4 py-3 font-medium">Quando</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-800/40 transition-colors">
                      <td className="px-4 py-3">
                        <span className="text-gray-200">
                          {log.admin_username || `#${log.admin_id}`}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-medium ${actionColor(log.action)}`}>
                          {actionLabel(log.action)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-400">
                        {log.target_type} #{log.target_id || "â€”"}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                        {log.details || "â€”"}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {timeAgo(log.timestamp)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {logTotal > 30 && (
              <div className="flex items-center justify-center gap-4 mt-4">
                <button
                  onClick={() => {
                    const p = Math.max(1, logPage - 1);
                    setLogPage(p);
                    fetchLogs(p);
                  }}
                  disabled={logPage <= 1}
                  className="p-2 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-gray-500">
                  PÃ¡gina {logPage} de {Math.ceil(logTotal / 30)}
                </span>
                <button
                  onClick={() => {
                    const p = logPage + 1;
                    setLogPage(p);
                    fetchLogs(p);
                  }}
                  disabled={logPage >= Math.ceil(logTotal / 30)}
                  className="p-2 rounded-lg bg-gray-800 text-gray-400 disabled:opacity-30 hover:bg-gray-700 transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}



