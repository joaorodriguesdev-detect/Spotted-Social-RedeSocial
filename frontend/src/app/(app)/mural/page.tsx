"use client";

import { useEffect, useState, useCallback } from "react";
import { Loader2, FileText, Trash2, Tag, Phone } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import apiClient, { extractErrorMessage } from "@/lib/api-client";
import type { MuralPost, MuralListResponse } from "@/types";
import SectionTabs from "@/components/SectionTabs";

function timeAgo(iso: string | null): string {
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

const CATEGORIES = [
  "Emprego", "Saude", "Geral", "Educacao",
  "Moradia", "Eventos", "Carona",
];

const CATEGORY_COLORS: Record<string, string> = {
  "Emprego": "from-blue-500 to-blue-700",
  "Saude": "from-green-500 to-emerald-700",
  "Geral": "from-purple-500 to-pink-600",
  "Educacao": "from-yellow-500 to-orange-600",
  "Moradia": "from-teal-500 to-cyan-600",
  "Eventos": "from-red-500 to-rose-600",
  "Carona": "from-indigo-500 to-violet-600",
};

export default function MuralPage() {
  const { user } = useAuth();

  const [posts, setPosts] = useState<MuralPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const fetchMural = useCallback(async (p: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {
        page: p,
        per_page: 12,
      };
      if (categoryFilter) {
        params.category = categoryFilter;
      }

      const response = await apiClient.get<MuralListResponse>("/api/mural/", { params });
      const data = response.data;
      setPosts(data.items);
      setTotal(data.total);
      setPage(data.page);
      setTotalPages(data.total_pages);
    } catch (err) {
      console.error("[Mural.fetchMural] erro ao carregar mural:", err);
      // Log detalhado para depuracao de Network Error
      if ((err as any)?.response) {
        console.error("  status:", (err as any).response.status);
        console.error("  data:", (err as any).response.data);
      } else {
        console.error("  Sem resposta do servidor (Network Error)");
      }
      setError(extractErrorMessage(err));
      setPosts([]);
      setTotal(0);
      setTotalPages(0);
      setPage(1);
    } finally {
      setLoading(false);
    }
  }, [categoryFilter]);

  useEffect(() => {
    fetchMural(1);
  }, [fetchMural]);

  // Recarrega lista quando um mural for criado
  useEffect(() => {
    function handleMuralCreated() {
      fetchMural(1);
    }
    window.addEventListener("mural-created", handleMuralCreated);
    return () => window.removeEventListener("mural-created", handleMuralCreated);
  }, [fetchMural]);

  const handleDelete = async (id: number) => {
    if (!confirm("Deletar este anuncio?")) return;
    try {
      await apiClient.delete(`/api/mural/${id}`);
      await fetchMural(page);
    } catch (err) {
      console.error("[Mural.handleDelete] erro ao excluir:", err);
      setError(extractErrorMessage(err));
    }
  };

  if (loading && posts.length === 0) {
    return (
      <main className="min-h-screen bg-black text-zinc-100 pb-28">
        <SectionTabs />
        <div className="mx-auto max-w-4xl px-4 py-6 min-h-[calc(100vh-12rem)] flex items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-violet-400" />
        </div>
      </main>
    );
  }

  if (error && posts.length === 0) {
    return (
      <main className="min-h-screen bg-black text-zinc-100 pb-28">
        <SectionTabs />
        <div className="mx-auto max-w-4xl px-4 py-6 min-h-[calc(100vh-12rem)] flex items-center justify-center">
          <div className="max-w-sm rounded-xl border border-red-800/40 bg-red-950/40 p-6 text-center">
            <p className="text-red-400 font-medium">{error}</p>
            <button
              onClick={() => fetchMural(1)}
              className="mt-4 px-4 py-2 rounded-lg bg-red-800/40 text-red-300 text-sm hover:bg-red-800/60"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-zinc-100 pb-28">
      <SectionTabs />
      <div className="mx-auto max-w-4xl px-4 py-6 space-y-6 min-h-[calc(100vh-12rem)]">
        <div className="flex items-center justify-between border-b border-purple-900/40 pb-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              Mural de Anuncios
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {total} anuncio(s) — Divulgue eventos, grupos e promocoes!
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setCategoryFilter(null)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              !categoryFilter
                ? "bg-purple-600/40 text-purple-300 border border-purple-500/50"
                : "bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600"
            }`}
          >
            Todas
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                categoryFilter === cat
                  ? "bg-purple-600/40 text-purple-300 border border-purple-500/50"
                  : "bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {posts.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <p className="text-gray-500">Nenhum anuncio no mural.</p>
            <p className="text-gray-600 text-sm mt-1">
              Seja o primeiro a divulgar algo!
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {posts.map((post) => (
                <article
                  key={post.id}
                  className="group relative rounded-xl border border-purple-900/30 bg-gray-900/60 backdrop-blur-sm p-5 transition-all duration-300 hover:border-purple-500/40 hover:shadow-[0_0_20px_-8px_rgba(168,85,247,0.3)]"
                >
                  <span
                    className={`inline-block px-2.5 py-1 rounded-full text-xs font-bold text-black bg-gradient-to-r ${
                      CATEGORY_COLORS[post.category] || "from-gray-500 to-gray-700"
                    } mb-3`}
                  >
                    <Tag className="w-3 h-3 inline mr-1" />
                    {post.category}
                  </span>

                  <h3 className="text-lg font-bold text-gray-100 mb-2 line-clamp-2">
                    {post.title}
                  </h3>

                  <p className="text-gray-300 text-sm leading-relaxed whitespace-pre-wrap break-words line-clamp-4 mb-3">
                    {post.content}
                  </p>

                  <div className="flex items-center gap-1.5 text-sm text-purple-400 mb-3">
                    <Phone className="w-3.5 h-3.5" />
                    <span className="truncate">{post.contact_info}</span>
                  </div>

                  <div className="flex items-center gap-2 pt-3 border-t border-purple-900/20 mt-auto">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-600 to-pink-600 flex items-center justify-center text-xs font-bold text-black shrink-0">
                      {(post.author_name || post.author_username || "?")[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-300 truncate">
                        {post.author_name || post.author_username || "Anonimo"}
                      </p>
                      <p className="text-[10px] text-gray-500">{timeAgo(post.timestamp)}</p>
                    </div>

                    {user && user.id === post.user_id && (
                      <button
                        onClick={() => handleDelete(post.id)}
                        className="p-1.5 text-gray-500 hover:text-red-400 transition-colors shrink-0"
                        title="Excluir"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2 pt-4">
                <button
                  onClick={() => fetchMural(page - 1)}
                  disabled={page <= 1 || loading}
                  className="px-4 py-2 rounded-lg bg-gray-800 text-gray-400 text-sm border border-gray-700 hover:border-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Anterior
                </button>
                <span className="text-sm text-gray-500">
                  Pagina {page} de {totalPages}
                </span>
                <button
                  onClick={() => fetchMural(page + 1)}
                  disabled={page >= totalPages || loading}
                  className="px-4 py-2 rounded-lg bg-gray-800 text-gray-400 text-sm border border-gray-700 hover:border-gray-600 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Proxima
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
