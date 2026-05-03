"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bell,
  CalendarDays,
  ClipboardList,
  Compass,
  Heart,
  Home,
  LogOut,
  MessageCircle,
  PlusSquare,
  Search,
  Send,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

// Itens do menu principal
const NAV_ITEMS = [
  { href: "/feed", label: "Feed", icon: Home },
  { href: "/explorar", label: "Explorar", icon: Compass },
  { href: "/direct", label: "Mensagens", icon: MessageCircle },
  { href: "/eventos", label: "Eventos", icon: CalendarDays },
  { href: "/mural", label: "Mural", icon: ClipboardList },
  { href: "/notificacoes", label: "Notificacoes", icon: Bell },
  { href: "/criar", label: "Criar", icon: PlusSquare },
];



function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Se não houver usuário logado, não renderiza a sidebar
  if (!user) return null;

  return (
    <aside className="fixed left-0 top-0 z-40 hidden h-screen w-64 flex-col border-r border-zinc-800/60 bg-black md:flex">
      {/* Logo */}
      <div className="flex h-16 items-center px-6">
        <Link href="/feed" className="text-xl font-black tracking-tight">
          <span className="bg-gradient-to-r from-emerald-400 to-violet-500 bg-clip-text text-transparent">
            Spotted
          </span>
        </Link>
      </div>

      {/* Navegacao principal */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/feed"
              ? pathname.startsWith("/feed")
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-4 rounded-xl px-4 py-3 text-sm font-medium transition-all ${isActive ? "bg-zinc-900 text-zinc-100" : "text-zinc-500 hover:bg-zinc-900/50 hover:text-zinc-200"}`}
            >
              <Icon
                className={`h-5 w-5 shrink-0 transition-colors ${isActive ? "text-emerald-400" : "text-zinc-500 group-hover:text-zinc-200"}`}
              />
              <span>{item.label}</span>
              {isActive && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-emerald-400" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Rodape: Perfil + Sair */}
      <div className="border-t border-zinc-800/60 px-3 py-3">
        {/* Perfil */}
        <Link
          href={`/perfil/${user.username}`}
          className={`group flex items-center gap-3 rounded-xl px-4 py-3 transition-all ${pathname.startsWith("/perfil") ? "bg-zinc-900" : "hover:bg-zinc-900/50"}`}
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-violet-500 p-[2px]">
            <div className="flex h-full w-full items-center justify-center rounded-full bg-black">
              <span className="text-[10px] font-bold text-zinc-100">
                {getInitials(user.name || user.username)}
              </span>
            </div>
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-zinc-100">
              {user.name || user.username}
            </p>
            <p className="truncate text-xs text-zinc-500">
              @{user.username}
            </p>
          </div>
        </Link>

        {/* Botao Sair */}
        <button
          onClick={logout}
          className="mt-1 flex w-full items-center gap-4 rounded-xl px-4 py-3 text-sm font-medium text-zinc-500 transition-all hover:bg-red-500/10 hover:text-red-400"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          <span>Sair</span>
        </button>
      </div>
    </aside>
  );
}
