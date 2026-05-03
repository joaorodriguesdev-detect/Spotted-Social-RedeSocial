/**
 * ───────────────────────────────────────────────────────────
 *  API Client – Spotted Social
 *  Centraliza todas as chamadas para o backend FastAPI
 *  Usa cookies httpOnly (JWT) via credentials: "include"
 * ───────────────────────────────────────────────────────────
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Helpers ───────────────────────────────────────────────────────────
function buildUrl(path: string, params?: Record<string, string | number>): string {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      url.searchParams.set(key, String(val));
    });
  }
  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: `Erro ${res.status}` }));
    throw new ApiError(res.status, errorBody.detail || `Erro ${res.status}`, errorBody);
  }

  if (res.status === 204) return undefined as unknown as T;

  return res.json();
}

// ── Error class customizada ──────────────────────────────────────────
export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

// ── Tipos compartilhados ─────────────────────────────────────────────
export interface UserBrief {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
}

export interface Post {
  id: number;
  content: string;
  media_url: string | null;
  timestamp: string | null;
  likes: number;
  user_id: number | null;
  is_anonymous: boolean;
  liked_by_me: boolean;
  author_username: string | null;
  author_name: string | null;
  author_profile_pic: string | null;
  comment_count: number;
}

export interface FeedResponse {
  items: Post[];
  has_more: boolean;
  next_cursor_ts?: string | null;
  next_cursor_id?: number | null;
  page?: number;
  limit?: number;
  total_count?: number;
}

// ── API Namespace ────────────────────────────────────────────────────
export const api = {
  auth: {
    login: (username: string, password: string) =>
      request<{ user_id: number; username: string; name: string | null; profile_pic: string | null; is_admin: boolean }>(
        "/auth/login",
        {
          method: "POST",
          body: JSON.stringify({ username: username.trim().toLowerCase(), password }),
        }
      ),

    register: (data: {
      username: string;
      name?: string;
      password: string;
      university?: string;
    }) =>
      request<{ user_id: number; username: string; name: string | null }>(
        "/auth/registro",
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),

    me: () => request<UserBrief>("/auth/me"),

    logout: () => request<void>("/auth/logout", { method: "POST" }),
  },

  feed: {
    list: (params?: { cursor_ts?: string; cursor_id?: number; page?: number; limit?: number }) =>
      request<FeedResponse>(buildUrl("/api/feed/", params as Record<string, string | number>)),

    like: (postId: number) =>
      request<{ liked: boolean; likes: number }>(`/api/feed/${postId}/like`, { method: "POST" }),

    create: (data: { content: string; media_url?: string; is_anonymous?: boolean }) =>
      request<Post>("/api/feed/", { method: "POST", body: JSON.stringify(data) }),
  },

  perfil: {
    get: (username: string) =>
      request<any>(`/api/perfil/${username}`),

    update: (data: {
      name?: string | null;
      bio?: string | null;
      social_link?: string | null;
      university?: string | null;
    }) =>
      request<UserBrief>("/api/perfil/update", {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    updatePhoto: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<{ ok: boolean; profile_pic: string; url: string }>("/api/perfil/update-photo", {
        method: "PUT",
        body: formData,
      });
    },
  },

  follow: {
    follow: (userId: number) => request<void>(`/api/follow/${userId}`, { method: "POST" }),
    unfollow: (userId: number) => request<void>(`/api/unfollow/${userId}`, { method: "DELETE" }),
  },

  notifications: {
    list: (skip = 0, limit = 20) =>
      request<{ items: any[]; unread_count: number; total: number }>(
        buildUrl("/api/notifications/", { skip, limit })
      ),

    unreadCount: () =>
      request<{ unread_count: number }>("/api/notifications/unread-count"),

    markRead: (notifId: number) =>
      request<void>(`/api/notifications/${notifId}/read`, { method: "PATCH" }),

    markAllRead: () =>
      request<void>("/api/notifications/read-all", { method: "PATCH" }),
  },

  chat: {
    conversations: () =>
      request<{ items: any[] }>("/api/chat/conversations"),

    history: (otherUserId: number) =>
      request<{ messages: any[]; is_online: boolean; conversation_id: number }>(
        `/api/chat/history/${otherUserId}`
      ),

    send: (otherUserId: number, content: string) =>
      request<any>(`/api/chat/send/${otherUserId}`, {
        method: "POST",
        body: JSON.stringify({ content }),
      }),
  },

  mural: {
    list: (params?: { skip?: number; limit?: number }) =>
      request<{ items: any[]; total: number }>(
        buildUrl("/api/mural/", params as Record<string, string | number>)
      ),

    create: (data: { content: string; media_url?: string; link?: string }) =>
      request<any>("/api/mural/", { method: "POST", body: JSON.stringify(data) }),

    delete: (muralId: number) =>
      request<void>(`/api/mural/${muralId}`, { method: "DELETE" }),
  },

  admin: {
    stats: () => request<any>("/api/admin/stats"),
    users: (params?: { page?: number; per_page?: number; search?: string }) =>
      request<{ items: any[]; total: number }>(
        buildUrl("/api/admin/users", params as Record<string, string | number>)
      ),
    logs: (params?: { page?: number; per_page?: number }) =>
      request<{ items: any[]; total: number }>(
        buildUrl("/api/admin/logs", params as Record<string, string | number>)
      ),
    toggleBan: (userId: number) =>
      request<void>(`/api/admin/users/${userId}/ban`, { method: "PATCH" }),
    deletePost: (postId: number) =>
      request<void>(`/api/admin/posts/${postId}`, { method: "DELETE" }),
  },
};

// ── Helpers utilitários ──────────────────────────────────────────────
export function timeAgo(iso: string | null): string {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "agora";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d`;
  return new Date(iso).toLocaleDateString("pt-BR");
}

export default api;
