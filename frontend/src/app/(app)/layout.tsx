"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2, LogOut, Send } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";
import MobileNavbar from "@/components/MobileNavbar";
import FloatingButton from "@/components/FloatingButton";
import { PostProvider } from "@/context/PostContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-zinc-400">
        <p className="text-sm">Faça login para acessar.</p>
      </div>
    );
  }

  const initialPosts: any[] = [];

  return (
    <PostProvider initialPosts={initialPosts}>
      <div className="min-h-screen bg-black">
      {/* Sidebar fixa (desktop) */}
      <Sidebar />

      {/* ── Mobile Header ─────────────────────────────────────────── */}
      <header className="fixed left-0 right-0 top-0 z-50 border-b border-zinc-800/60 bg-black/90 backdrop-blur-xl md:hidden">
        <div className="flex h-14 items-center justify-between px-4">
          <button
            onClick={() => logout()}
            className="rounded-full p-2 text-zinc-500 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
            aria-label="Sair"
          >
            <LogOut className="h-5 w-5" />
          </button>

          <span className="text-lg font-black tracking-tight">
            <span className="bg-gradient-to-r from-emerald-400 to-violet-500 bg-clip-text text-transparent">
              Spotted
            </span>
          </span>

          <Link href="/direct" className="rounded-full p-2 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-100" aria-label="Mensagens"><Send className="h-5 w-5" /></Link>
        </div>
      </header>

      {/* Conteúdo principal */}
      <div className="pt-14 md:pt-0 md:ml-64">{children}</div>

      {/* FAB dispatcher – renderiza o botão correto conforme a rota */}
      <FloatingButton />

      {/* Navbar mobile */}
      <MobileNavbar username={user.username} />
      </div>
    </PostProvider>
  );
}


