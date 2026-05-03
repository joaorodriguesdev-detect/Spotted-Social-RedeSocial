/** @type {import('next').NextConfig} */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  // ── Proxy de API: redireciona para o backend FastAPI ────────────
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL}/api/:path*`,
      },
      {
        source: "/auth/:path*",
        destination: `${API_URL}/auth/:path*`,
      },
      {
        source: "/users/:path*",
        destination: `${API_URL}/users/:path*`,
      },
      {
        source: "/cupons/:path*",
        destination: `${API_URL}/cupons/:path*`,
      },
      // Uploads (fotos de perfil, posts, etc.)
      {
        source: "/static/uploads/:path*",
        destination: `${API_URL}/static/uploads/:path*`,
      },
    ];
  },

  // ── Imagens externas (uploads do backend) ─────────────────────────
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/static/uploads/**",
      },
      {
        protocol: "http",
        hostname: "127.0.0.1",
        port: "8000",
        pathname: "/static/uploads/**",
      },
      {
        protocol: "https",
        hostname: "**",
        pathname: "/static/uploads/**",
      },
    ],
  },

  // ── Headers de segurança adicionais ───────────────────────────────
  async headers() {
    return [
      {
        source: "/api/:path*",
        headers: [
          { key: "Access-Control-Allow-Origin", value: "*" },
          { key: "Access-Control-Allow-Credentials", value: "true" },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
