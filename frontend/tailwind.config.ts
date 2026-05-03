import type { Config } from "tailwindcss";

const config: Config = {
  // Garante que o Tailwind procure estilos em todas as pastas do seu Next.js
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Adicionando tons de zinco para um modo escuro mais profundo
        zinc: {
          950: "#09090b",
        },
        // Definindo o Roxo (Violet) como a cor principal do Spotted Social
        violet: {
          400: "#a78bfa",
          500: "#8b5cf6",
          600: "#7c3aed",
          700: "#6d28d9",
        },
      },
      // Mantendo a animação, mas agora com a cor roxa
      animation: {
        "glow-pulse": "glow-pulse 2s ease-in-out infinite",
      },
      keyframes: {
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 20px -5px rgba(124,58,237,0.3)" },
          "50%": { boxShadow: "0 0 30px -3px rgba(124,58,237,0.6)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;