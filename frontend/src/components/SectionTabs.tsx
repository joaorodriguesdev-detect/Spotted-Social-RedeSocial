"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const tabs = [
  { href: "/feed", label: "Feed", match: (pathname: string) => pathname.startsWith("/feed") },
  { href: "/eventos", label: "Eventos", match: (pathname: string) => pathname.startsWith("/eventos") },
  { href: "/mural", label: "Mural", match: (pathname: string) => pathname.startsWith("/mural") },
];

export default function SectionTabs() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-zinc-800/60 bg-black">
      <div className="mx-auto w-full max-w-3xl px-4">
        <div className="grid grid-cols-3">
          {tabs.map((tab) => {
            const active = tab.match(pathname);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={`relative py-3.5 text-center text-sm font-semibold transition-colors ${
                  active
                    ? "text-zinc-50"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {tab.label}
                {/* Indicador de aba ativa — borda inferior grossa e definida */}
                <span
                  className={`absolute inset-x-0 bottom-0 h-[3px] rounded-t-sm transition-all duration-200 ${
                    active
                      ? "bg-violet-500 shadow-[0_0_12px_rgba(139,92,246,0.4)]"
                      : "bg-transparent"
                  }`}
                />
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}

