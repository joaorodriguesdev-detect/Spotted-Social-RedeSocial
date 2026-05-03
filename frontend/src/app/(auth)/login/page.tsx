"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, Lock, LogIn, User } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { login, loading: authLoading, error: authError, clearError } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    clearError();

    if (!username.trim()) {
      setError("Digite seu nome de usuário.");
      return;
    }

    if (!password) {
      setError("Digite sua senha.");
      return;
    }

    setSubmitting(true);

    try {
      const success = await login(username.trim().toLowerCase(), password);
      if (success) {
        router.push("/");
      } else {
        setError(authError || "Credenciais inválidas. Tente novamente.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro de conexão com o servidor.");
    } finally {
      setSubmitting(false);
    }
  };

  const isBusy = submitting || authLoading;

  return (
    <div className="auth-shell flex flex-col md:flex-row items-center justify-center gap-20 px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(124,58,237,0.18),_transparent_32%),radial-gradient(circle_at_bottom,_rgba(124,58,237,0.08),_transparent_24%)]" />

      <section className="relative z-10 w-full max-w-xl text-center md:text-left">
        <div className="mb-6 inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.35em] text-zinc-400 md:justify-start">
          Spotted Social
        </div>
        <h1 className="text-5xl font-black tracking-tight text-zinc-100 sm:text-6xl lg:text-7xl">
          Spotted
        </h1>
        <p className="mx-auto mt-4 max-w-md text-sm leading-6 text-zinc-400 md:mx-0 sm:text-base">
          Compartilhe segredos e momentos da sua universidade com total liberdade.
        </p>
      </section>

      <div className="relative z-10 w-full max-w-md">
        <div className="auth-card w-full">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="login-username" className="sr-only">
                Usuário
              </label>
              <div className="group relative">
                <User className="auth-icon" />
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Usuário (seu @usuario)"
                  autoComplete="username"
                  autoFocus
                  disabled={isBusy}
                  className="auth-input pl-11"
                />
              </div>
            </div>

            <div>
              <label htmlFor="login-password" className="sr-only">
                Senha
              </label>
              <div className="group relative">
                <Lock className="auth-icon" />
                                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Senha"
                  autoComplete="current-password"
                  maxLength={72}
                  disabled={isBusy}
                  className="auth-input pl-11 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 transition-colors hover:text-zinc-200 disabled:opacity-50"
                  tabIndex={-1}
                  disabled={isBusy}
                  aria-label={showPassword ? "Esconder senha" : "Mostrar senha"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={isBusy} className="auth-button">
              {isBusy ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Entrando...
                </>
              ) : (
                <>
                  <LogIn className="h-4 w-4" />
                  Entrar
                </>
              )}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-zinc-500">bem-vindo(a)</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <p className="text-center text-sm text-zinc-400">
            Não tem uma conta?{" "}
            <Link href="/registro" className="auth-link">
              Cadastre-se
            </Link>
          </p>
        </div>

        <p className="mt-8 text-center text-[11px] uppercase tracking-[0.35em] text-zinc-600">
          Spotted Social © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  );
}