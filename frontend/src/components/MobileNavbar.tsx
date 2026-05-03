"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Home, Search, Send, User } from "lucide-react";
import Image from "next/image";
import { useState, useEffect } from "react";

interface MobileNavbarProps {
  username?: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const items = [
  { href: "/feed", label: "Feed", icon: Home, match: (path: string) => path.startsWith("/feed") },
  { href: "/explorar", label: "Explorar", icon: Search, match: (path: string) => path.startsWith("/explorar") },
  { href: "/direct", label: "DM", icon: Send, match: (path: string) => path.startsWith("/direct") },
  { href: "/notificacoes", label: "Notificacoes", icon: Bell, match: (path: string) => path.startsWith("/notificacoes") },
];

export default function MobileNavbar({ username }: MobileNavbarProps) {
  const pathname = usePathname();
  const [profilePic, setProfilePic] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/me`, { credentials: "include" });
        if (res.ok && res.status === 200) {
          const data = await res.json();
          if (data?.profile_pic) {
            setProfilePic(`${API_BASE}/static/uploads/${data.profile_pic}`);
          }
        }
      } catch { /* nao logado */ } finally { setLoading(false); }
    })();
  }, []);

  return (
    <div className="md:hidden fixed inset-x-0 bottom-0 z-50 border-t border-zinc-800/60 bg-black/90 backdrop-blur-xl">
      <div className="grid grid-cols-5 items-center px-2 py-1">
        {items.map((item) => {
          const active = item.match(pathname);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={"flex flex-col items-center gap-0.5 rounded-2xl py-2 text-[10px] font-medium transition-colors " + (active ? "text-emerald-400" : "text-zinc-500 hover:text-zinc-200")}
            >
              <Icon className={"h-5 w-5 " + (active ? "text-emerald-400" : "text-current")} />
              <span className="truncate">{item.label}</span>
            </Link>
          );
        })}

        {/* Perfil */}
        <Link
          href={username ? "/perfil/" + username : "/login"}
          className={"flex flex-col items-center gap-0.5 rounded-2xl py-2 text-[10px] font-medium transition-colors " + (pathname.startsWith("/perfil") ? "text-emerald-400" : "text-zinc-500 hover:text-zinc-200")}
        >
          {profilePic && !loading ? (
            <div className="h-5 w-5 rounded-full overflow-hidden border border-emerald-400/30">
              <Image src={profilePic} alt="Perfil" width={20} height={20} className="w-full h-full object-cover" unoptimized />
            </div>
          ) : (
            <User className={"h-5 w-5 " + (pathname.startsWith("/perfil") ? "text-emerald-400" : "text-current")} />
          )}
          <span className="truncate">Perfil</span>
        </Link>
      </div>
    </div>
  );
}
