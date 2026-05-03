import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { WebsocketProvider } from "@/context/WebsocketContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  metadataBase: new URL("http://localhost:3000"),
  title: "Spotted Social",
  description: "Rede social Dark Premium — Conecte-se, compartilhe, descubra.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className="!bg-black !text-zinc-100">
      <body
        className={`${inter.className} min-h-dvh !bg-black !text-zinc-100 antialiased`}
      >
        <AuthProvider>
          <WebsocketProvider>{children}</WebsocketProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

