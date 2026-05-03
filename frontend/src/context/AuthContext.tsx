﻿/**
 * â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 *  AuthContext â€“ Provedor de AutenticaÃ§Ã£o Global
 *  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 *  MantÃ©m o estado do usuÃ¡rio logado em toda a aplicaÃ§Ã£o.
 *  PersistÃªncia: usa cookies httpOnly (JWT) â€” o backend gerencia.
 *  O client armazena apenas um cache leve em localStorage para
 *  hidrataÃ§Ã£o instantÃ¢nea entre reloads.
 *
 *  Uso:
 *    const { user, loading, login, logout } = useAuth();
 *
 *    await login("username", "password");  â†’ redireciona para /feed
 *    await logout();                       â†’ redireciona para /login
 * â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 */

"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import apiClient, { extractErrorMessage } from "@/lib/api-client";
import type { AuthResponse } from "@/types";

// â”€â”€ Tipos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export interface AuthUser {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
  is_admin: boolean;
}

interface AuthContextValue {
  /** Dados do usuÃ¡rio logado, ou null se nÃ£o autenticado */
  user: AuthUser | null;
  /** Token JWT do usuÃ¡rio, ou null */
  token: string | null;
  /** True enquanto verifica sessÃ£o no mount */
  loading: boolean;
  /** Mensagem de erro da Ãºltima operaÃ§Ã£o */
  error: string | null;
  /** Fazer login â€” retorna true em sucesso */
  login: (username: string, password: string) => Promise<boolean>;
  /** Fazer logout â€” limpa sessÃ£o e redireciona */
  logout: () => Promise<void>;
  /** Limpa o estado de erro */
  clearError: () => void;
  /** Recarrega os dados do usuÃ¡rio via /auth/me */
  refresh: () => Promise<void>;
}

// â”€â”€ Context â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const AUTH_STORAGE_KEY = "spotted_auth_user";

// â”€â”€ Provider â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true); // true atÃ© checar sessÃ£o
  const [error, setError] = useState<string | null>(null);

  /**
   * refresh â€“ Busca os dados do usuÃ¡rio atual via /auth/me.
   * Usado no mount para restaurar sessÃ£o via cookie.
   */
  const refresh = useCallback(async () => {
    try {
      const response = await apiClient.get<AuthResponse>("/auth/me");
      const data = response.data;
      const authUser: AuthUser = {
        id: data.user_id,
        username: data.username,
        name: data.name ?? null,
        profile_pic: data.profile_pic ?? null,
        is_admin: data.is_admin ?? false,
      };
      setUser(authUser);
      setError(null);

      // Cache local para hidrataÃ§Ã£o instantÃ¢nea
      try {
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
      } catch {
        // Ambiente SSR ou sem permissÃ£o
      }
      // Guarda token JWT do /auth/me
      if (data.token) {
        try {
          setToken(data.token);
          sessionStorage.setItem("spotted_jwt", data.token);
        } catch {
          // Ignora
        }
      }
    } catch {
      // 401 ou erro de rede â†’ nÃ£o autenticado
      setUser(null);
      setToken(null);
      try {
        localStorage.removeItem(AUTH_STORAGE_KEY);
      } catch {
        // Ignora
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // â”€â”€ Verifica sessÃ£o no mount â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  useEffect(() => {
    let isMounted = true;

    const checkAuth = async () => {
      // Tenta hidrataÃ§Ã£o instantÃ¢nea do cache local
      try {
        const cached = localStorage.getItem(AUTH_STORAGE_KEY);
        if (cached && isMounted) {
          const parsed = JSON.parse(cached) as AuthUser;
          if (parsed?.id && parsed?.username) {
            setUser(parsed);
          }
        }
        const jwt = sessionStorage.getItem("spotted_jwt");
        if (jwt && isMounted) {
          setToken(jwt);
        }
      } catch {
        // Cache invÃ¡lido, ignora
      }

      // Depois valida com o servidor (sobrescreve o cache se necessÃ¡rio)
      if (isMounted) {
        await refresh();
      }
    };

    checkAuth();

    return () => {
      isMounted = false;
    };
  }, [refresh]);

  // â”€â”€ Login â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const login = useCallback(
    async (username: string, password: string): Promise<boolean> => {
      setLoading(true);
      setError(null);

      try {
        const response = await apiClient.post<AuthResponse>("/auth/login", {
          username: username.trim().toLowerCase(),
          password,
        });

        const data = response.data;
        const authUser: AuthUser = {
          id: data.user_id,
          username: data.username,
          name: data.name ?? null,
          profile_pic: data.profile_pic ?? null,
          is_admin: data.is_admin ?? false,
        };

        setUser(authUser);
        setError(null);

        // Cache local
        try {
          localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        } catch {
          // Ignora
        }
        // Guarda token JWT para enviar via Authorization header
        if (data.token) {
          try {
            setToken(data.token);
            sessionStorage.setItem("spotted_jwt", data.token);
          } catch {
            // Ignora
          }
        }

        return true;
      } catch (err) {
        const msg = extractErrorMessage(err);
        setError(msg);
        return false;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // â”€â”€ Logout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Mesmo que a requisiÃ§Ã£o falhe, limpa localmente
    }

    setUser(null);
    setToken(null);
    setError(null);

    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      sessionStorage.removeItem("spotted_jwt");
    } catch {
      // Ignora
    }

    router.push("/login");
  }, [router]);

  // â”€â”€ Clear error â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const clearError = useCallback(() => setError(null), []);

  // â”€â”€ Value exposto â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  const value: AuthContextValue = {
    user,
    token,
    loading,
    error,
    login,
    logout,
    clearError,
    refresh,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// â”€â”€ Hook â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  }
  return ctx;
}
