/**
 * â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 *  API Client â€“ Spotted Social V2 (Axios)
 *  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 *  InstÃ¢ncia central do Axios com:
 *    â€¢ Base URL via NEXT_PUBLIC_API_URL
 *    â€¢ withCredentials: true para cookies httpOnly (JWT)
 *    â€¢ Interceptor de resposta: captura 401 â†’ limpa sessÃ£o â†’ /login
 *    â€¢ Interceptor de requisiÃ§Ã£o: contentType automÃ¡tico
 * â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

// â”€â”€ 1. InstÃ¢ncia â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// Usa baseURL vazio para que as requisiÃ§Ãµes passem pelo proxy do Next.js
// (rewrites em next.config.js), evitando CORS.
const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "";

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15_000,
});

// â”€â”€ 2. Interceptor de REQUISIÃ‡ÃƒO â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Se o corpo for FormData, remove o Content-Type para o browser
    // definir o boundary automaticamente
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }
    // Anexa token JWT se existir no sessionStorage (fallback para cookie)
    try {
      const token = sessionStorage.getItem("spotted_jwt");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // SSR ou sem permissÃ£o
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// â”€â”€ 3. Interceptor de RESPOSTA â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
// NOTA: NÃ£o tratamos 401/403 aqui porque endpoints como /api/mural/ podem
// retornar 401 mesmo com sessÃ£o vÃ¡lida (ex: endpoint nÃ£o existe no backend).
// O AuthContext gerencia a sessÃ£o exclusivamente via /auth/me.
// O layout jÃ¡ protege as rotas: se user===null, redireciona para /login.
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => Promise.reject(error)
);

// â”€â”€ 4. UtilitÃ¡rio para extrair mensagem de erro â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      // Erros de validaÃ§Ã£o Pydantic retornam array de ValidationError
      return detail.map((d) => `${d.msg || d.message || ""}`).join("; ");
    }
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Erro desconhecido";
}

export default apiClient;

// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
//  Helper: constrÃ³i URL com query params
// â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
export function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>
): string {
  // Se tiver NEXT_PUBLIC_API_URL configurada, usa URL absoluta
  // SenÃ£o, usa caminho relativo (passa pelo proxy Next.js)
  const base = process.env.NEXT_PUBLIC_API_URL || "";
  const url = new URL(`${base}${path}`, typeof window !== "undefined" ? window.location.origin : "http://localhost:3000");
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        url.searchParams.set(key, String(val));
      }
    });
  }
  return url.toString();
}

