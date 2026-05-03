// DEBUG - FRONTEND SPOTTED SOCIAL V2

// ════════════════════════════════════════════════════════════════════════════
// VERIFICAR LOADING INFINITO
// ════════════════════════════════════════════════════════════════════════════

// 1. Abra DevTools (F12)
// 2. Vá para Console
// 3. Digite:

// Verificar se context está carregado:
console.log(document.body.innerHTML.includes("Loader2") ? "Loading..." : "Carregado");

// Verificar localStorage:
console.log("Auth cache:", localStorage.getItem("spotted_auth_user"));

// Verificar se API está respondendo:
fetch("http://127.0.0.1:8000/auth/me", { credentials: "include" })
  .then(r => r.json())
  .then(d => console.log("User:", d))
  .catch(e => console.error("Erro:", e.message));

// ════════════════════════════════════════════════════════════════════════════
// VERIFICAR CORES NO BOTTOM NAV
// ════════════════════════════════════════════════════════════════════════════

// Deve mostrar "emerald-400" quando ativo:
document.querySelector("[href='/']").classList // Check classes

// ════════════════════════════════════════════════════════════════════════════
// VERIFICAR SE NAVBAR ESTÁ RENDERIZANDO
// ════════════════════════════════════════════════════════════════════════════

// Deve encontrar os botões:
console.log("Settings?", !!document.querySelector("button[title='Configurações']"));
console.log("Logout?", !!Array.from(document.querySelectorAll("button")).find(b => b.textContent.includes("Sair")));

// ════════════════════════════════════════════════════════════════════════════
// VERIFICAR PERFORMANCE
// ════════════════════════════════════════════════════════════════════════════

// Performance timing:
window.addEventListener("load", () => {
  console.log("Time to interactive:", performance.timing.loadEventEnd - performance.timing.navigationStart, "ms");
});

// ════════════════════════════════════════════════════════════════════════════
// NETWORK TAB (F12 → Network)
// ════════════════════════════════════════════════════════════════════════════

// Procure por erros 401 (não autenticado)
// Procure por erros 500 (servidor)
// Procure por timing lento em /auth/me

// ════════════════════════════════════════════════════════════════════════════
// SE AINDA TIVER LOADING INFINITO
// ════════════════════════════════════════════════════════════════════════════

// 1. Limpar cache do navegador:
// DevTools → Application → Clear Site Data

// 2. Parar e reiniciar frontend:
// Ctrl+C no terminal
// npm run dev

// 3. Se persistir, desabilitar cache:
// Firefox: about:config → network.http.use-cache: false
// Chrome: DevTools → Settings → Network → Disable cache

// 4. Forçar rebuild:
// npm run build
// npm run dev

// ════════════════════════════════════════════════════════════════════════════
// VERIFICAR LOGS DO SERVIDOR
// ════════════════════════════════════════════════════════════════════════════

// Backend FastAPI (Terminal):
// Procure por:
// - GET /auth/me 200 (sucesso)
// - GET /auth/me 401 (não autenticado - normal)
// - GET /auth/me 500 (erro - problema)

// Frontend Next.js (Terminal):
// Procure por:
// - Compiled successfully
// - Error: ... (se houver erro)
// - Ready in X.XXs

// ════════════════════════════════════════════════════════════════════════════
// ENVIROMENT VARIABLES
// ════════════════════════════════════════════════════════════════════════════

// Verificar se NEXT_PUBLIC_API_URL está definida no .env.local:
// NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

// Se não existir, será usado fallback: http://127.0.0.1:8000

// ════════════════════════════════════════════════════════════════════════════
// COMMON ISSUES & FIXES
// ════════════════════════════════════════════════════════════════════════════

/*
ISSUE: "Loading... Loading... (infinito)"
FIX:
1. Verificar se /auth/me retorna 401
2. Se retorna 401, é normal → redireciona para /login
3. Se retorna 500, há erro no backend
4. Se nunca retorna, backend não está respondendo

ISSUE: "Cores não estão esmeralda no Bottom Nav"
FIX:
1. Verificar em DevTools inspect se classes tailwind estão aplicadas
2. Tailwind config pode estar desatualizado
3. Executar: npm run build

ISSUE: "Settings/Logout não aparecem no Header"
FIX:
1. Pode estar em mobile (< 768px)
2. Verificar se useAuth() retorna user
3. Verificar className="hidden md:inline-flex"

ISSUE: "Avatar mostra spinner ao invés de foto"
FIX:
1. Fazer upload de foto em /perfil/editar
2. Ou recarregar página (Ctrl+R)
3. Verificar localStorage auth cache

ISSUE: "Blank page / 404"
FIX:
1. Verificar se está em http://localhost:3000
2. Não em http://localhost:3000/
3. Não em http://127.0.0.1:3000
4. DevTools Console pode ter mais info
*/

// ════════════════════════════════════════════════════════════════════════════
// SCRIPT DE DEBUG RÁPIDO
// ════════════════════════════════════════════════════════════════════════════

// Cole este script inteiro no DevTools Console:
(function debugSpotted() {
  console.group("🔍 Spotted Debug Report");
  console.log("URL:", window.location.href);
  console.log("Auth cache:", localStorage.getItem("spotted_auth_user") ? "✅" : "❌");
  console.log("Page ready:", document.readyState);

  fetch("http://127.0.0.1:8000/auth/me", { credentials: "include" })
    .then(r => ({ status: r.status, text: r.statusText }))
    .then(d => console.log("Backend:", `${d.status} ${d.text}`))
    .catch(e => console.error("Backend error:", e.message));

  console.groupEnd();
})();

// ════════════════════════════════════════════════════════════════════════════
// SE TUDO FALHAR
// ════════════════════════════════════════════════════════════════════════════

/*
1. Parar ambos servidores (Ctrl+C em cada terminal)
2. Limpar .next cache:
   rm -r frontend/.next
3. Reinstalar dependências:
   npm install
4. Rebuild:
   npm run build
5. Reiniciar:
   npm run dev
*/

