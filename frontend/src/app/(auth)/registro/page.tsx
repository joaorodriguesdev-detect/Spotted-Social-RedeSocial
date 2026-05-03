"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, UserPlus, Lock, User, School } from "lucide-react";
import Link from "next/link";
import apiClient from "@/lib/api-client";

interface RegisterResponse {
  user_id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
  is_admin: boolean;
  token?: string;
}

const UNIVERSITIES = [
  "UFPR (Federal)",
  "UTFPR",
  "PUCPR",
  "UP (Positivo)",
  "UTP (Tuiuti)",
  "UniCuritiba",
  "FAE",
  "Outra",
];

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [university, setUniversity] = useState("UFPR (Federal)");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim()) {
      setError("Digite um nome de usuário.");
      return;
    }
    if (username.trim().length < 3) {
      setError("O usuário deve ter pelo menos 3 caracteres.");
      return;
    }
    if (!/^[a-z0-9_]+$/.test(username.trim())) {
      setError("Use apenas letras minúsculas, números e underscore (_).");
      return;
    }
    if (!password) {
      setError("Digite uma senha.");
      return;
    }
    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }
    if (!/[#@$%*]/.test(password)) {
      setError("A senha deve incluir ao menos um destes: # @ $ % *");
      return;
    }
    if (password !== confirmPassword) {
      setError("As senhas não conferem.");
      return;
    }

    setLoading(true);

    try {
      await apiClient.post<RegisterResponse>("/auth/registro", {
        username: username.trim().toLowerCase(),
        name: name.trim() || username.trim(),
        password,
        confirm_password: confirmPassword,
        university,
      });

      router.push("/");
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const errorText =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail[0]?.msg || err?.message
            : err?.message;
      setError(errorText || "Erro ao cadastrar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell flex items-center justify-center px-4 py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(124,58,237,0.18),_transparent_32%),radial-gradient(circle_at_bottom,_rgba(124,58,237,0.08),_transparent_24%)]" />
      <div className="relative z-10 flex w-full max-w-md flex-col items-center">
        <div className="mb-10 text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.35em] text-zinc-400">
            Spotted Social
          </div>
          <h1 className="text-5xl font-black tracking-tight text-zinc-100 sm:text-6xl">Spotted</h1>
          <p className="mt-4 max-w-sm text-sm leading-6 text-zinc-400 sm:text-base">
            Crie sua conta e entre no ecossistema premium da comunidade.
          </p>
        </div>

        <div className="auth-card w-full">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="reg-username" className="auth-label sr-only">
                Usuário
              </label>
              <div className="group relative">
                <User className="auth-icon group-focus-within:text-violet-400" />
                <input
                  id="reg-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Seu usuário"
                  autoComplete="username"
                  autoFocus
                  maxLength={30}
                  disabled={loading}
                  className="auth-input pl-11"
                />
              </div>
            </div>

            <div>
              <label htmlFor="reg-name" className="auth-label sr-only">
                Nome
              </label>
              <div className="group relative">
                <User className="auth-icon group-focus-within:text-violet-400" />
                <input
                  id="reg-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Seu nome (opcional)"
                  maxLength={80}
                  disabled={loading}
                  className="auth-input pl-11"
                />
              </div>
            </div>

            <div>
              <label htmlFor="reg-university" className="auth-label sr-only">
                Universidade
              </label>
              <div className="group relative">
                <School className="auth-icon group-focus-within:text-violet-400" />
                <select
                  id="reg-university"
                  value={university}
                  onChange={(e) => setUniversity(e.target.value)}
                  disabled={loading}
                  className="auth-input pl-11 pr-10 appearance-none"
                >
                  {UNIVERSITIES.map((uni) => (
                    <option key={uni} value={uni} className="bg-zinc-900 text-zinc-100">
                      {uni}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label htmlFor="reg-password" className="auth-label sr-only">
                Senha
              </label>
              <div className="group relative">
                <Lock className="auth-icon group-focus-within:text-violet-400" />
                                <input
                  id="reg-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Senha"
                  autoComplete="new-password"
                  maxLength={72}
                  disabled={loading}
                  className="auth-input pl-11 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 transition-colors hover:text-zinc-200 disabled:opacity-50"
                  tabIndex={-1}
                  disabled={loading}
                  aria-label={showPassword ? "Esconder senha" : "Mostrar senha"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="reg-confirm" className="auth-label sr-only">
                Confirmar senha
              </label>
              <div className="group relative">
                <Lock className="auth-icon group-focus-within:text-violet-400" />
                                <input
                  id="reg-confirm"
                  type={showConfirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirmar senha"
                  autoComplete="new-password"
                  maxLength={72}
                  disabled={loading}
                  className="auth-input pl-11 pr-11"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 transition-colors hover:text-zinc-200 disabled:opacity-50"
                  tabIndex={-1}
                  disabled={loading}
                  aria-label={showConfirm ? "Esconder senha" : "Mostrar senha"}
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="auth-hint space-y-1.5">
              <p className={password.length >= 8 ? "text-emerald-400" : ""}>
                {password.length >= 8 ? "✓" : "○"} Mínimo 8 caracteres
              </p>
              <p className={/[#@$%*]/.test(password) ? "text-emerald-400" : ""}>
                {/[#@$%*]/.test(password) ? "✓" : "○"} Incluir # @ $ % *
              </p>
              <p className={password === confirmPassword && password ? "text-emerald-400" : ""}>
                {password === confirmPassword && password ? "✓" : "○"} Senhas conferem
              </p>
            </div>

            <button type="submit" disabled={loading} className="auth-button">
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Criando conta…
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  Criar conta
                </>
              )}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-white/10" />
            <span className="text-xs font-medium uppercase tracking-[0.3em] text-zinc-500">ou</span>
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <p className="text-center text-sm text-zinc-400">
            Já tem conta?{" "}
            <Link href="/login" className="auth-link">
              Entrar
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

