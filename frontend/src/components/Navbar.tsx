"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Settings, LogOut } from "lucide-react";
import NotificationBell from "./NotificationBell";
import MobileNavbar from "./MobileNavbar";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();


  const handleLogout = async () => {
    await logout();
  };

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-white/10 bg-black/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4">
          <Link
            href="/"
            className="text-lg font-bold tracking-tight bg-gradient-to-r from-emerald-400 via-violet-400 to-violet-600 bg-clip-text text-transparent"
          >
            Spotted
          </Link>

          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="hidden md:block">
                  <NotificationBell />
                </div>

                <button
                  onClick={() => router.push("/perfil/editar")}
                  className="hidden md:inline-flex items-center justify-center p-2 rounded-full hover:bg-white/5 transition-colors text-zinc-400 hover:text-zinc-100"
                  title="Configurações"
                >
                  <Settings className="h-5 w-5" />
                </button>

                <button
                  onClick={handleLogout}
                  className="hidden md:inline-flex items-center gap-2 rounded-full border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm font-semibold text-red-300 transition-all hover:bg-red-500/20"
                >
                  <LogOut className="h-4 w-4" />
                  Sair
                </button>
              </>
            ) : null}
          </div>
        </div>
      </header>

      <MobileNavbar username={user?.username ?? null} />
    </>
  );
}
