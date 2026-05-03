"use client";

import { useState, useEffect, useRef } from "react";
import { Search, X, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import apiClient from "@/lib/api-client";

interface SearchResult {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
  is_verified: boolean;
  followers_count: number;
}

function getInitials(value: string | null): string {
  return value?.trim()?.[0]?.toUpperCase() ?? "?";
}

export default function SearchBar() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // ── Debounce: só pesquisa após 400ms sem digitar ──────────────
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await apiClient.get<SearchResult[]>("/users/search", {
          params: { q: query.trim() },
        });
        const data = response.data || [];
        setResults(data);
        setOpen(data.length > 0);
      } catch {
        setResults([]);
        setOpen(false);
      } finally {
        setLoading(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [query]);

  // ── Fecha dropdown ao clicar fora ─────────────────────────────
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function handleSelect(username: string) {
    setOpen(false);
    setQuery("");
    router.push(`/perfil/${username}`);
  }

  return (
    <div className="relative w-full">
      {/* ── Input com lupa ────────────────────────────────────── */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.trim()) setOpen(true);
          }}
          onFocus={() => {
            if (results.length > 0) setOpen(true);
          }}
          placeholder="Buscar pessoas..."
          className="w-full rounded-full border border-zinc-800/60 bg-zinc-900/50 py-2.5 pl-10 pr-10 text-sm text-zinc-100 outline-none transition-colors placeholder-zinc-500 focus:border-violet-500/50 focus:bg-zinc-900"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setResults([]);
              setOpen(false);
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 transition-colors hover:text-zinc-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* ── Dropdown de resultados ────────────────────────────── */}
      {open && query.trim() && (
        <div
          ref={dropdownRef}
          className="absolute left-0 right-0 top-full z-50 mt-2 overflow-hidden rounded-xl border border-zinc-800/60 bg-zinc-900 shadow-2xl shadow-black/50"
        >
          {loading ? (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-violet-400" />
            </div>
          ) : results.length === 0 ? (
            <div className="py-6 text-center text-sm text-zinc-500">
              Nenhum usuário encontrado
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {results.map((user) => (
                <button
                  key={user.id}
                  onClick={() => handleSelect(user.username)}
                  className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-zinc-800/60"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400/30 to-violet-500/30 text-sm font-bold text-violet-400">
                    {getInitials(user.name || user.username)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-zinc-100">
                      {user.name || user.username}
                      {user.is_verified && (
                        <span className="ml-1 text-[10px] text-emerald-400">✓</span>
                      )}
                    </p>
                    <p className="truncate text-xs text-zinc-500">@{user.username}</p>
                  </div>
                  <span className="shrink-0 text-xs text-zinc-600">
                    {user.followers_count} seguidores
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
