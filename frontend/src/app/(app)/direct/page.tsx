"use client";

import { useState, useEffect, Suspense, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Loader2, MessageSquare } from "lucide-react";

import Chat from "@/components/Chat";
import apiClient from "@/lib/api-client";
import { useAuth } from "@/context/AuthContext";

interface OtherUser {
  id: number;
  username: string;
  name: string | null;
  profile_pic: string | null;
}

// Componente principal que contém a lógica
function DirectMessages() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user: currentUser, loading: authLoading, token } = useAuth();

  const [selectedUser, setSelectedUser] = useState<OtherUser | null>(null);
  const [loadingChat, setLoadingChat] = useState(true);

  const fetchAndSetUser = useCallback(async (username: string) => {
    setLoadingChat(true);
    try {
      const response = await apiClient.get(`/api/perfil/${username}`);
      const profile = response.data;
      setSelectedUser({
        id: profile.id,
        username: profile.username,
        name: profile.name,
        profile_pic: profile.profile_pic,
      });
    } catch (err) {
      console.error("Falha ao buscar usuário para o chat:", err);
      router.replace('/direct'); // Volta para a lista se o usuário não for encontrado
    } finally {
      setLoadingChat(false);
    }
  }, [router]);

  useEffect(() => {
    const targetUsername = searchParams.get("with_user");
    if (targetUsername) {
      fetchAndSetUser(targetUsername);
    } else {
      setSelectedUser(null);
      setLoadingChat(false);
    }
  }, [searchParams, fetchAndSetUser]);

  const handleBackToList = () => {
    setSelectedUser(null);
    router.replace('/direct'); // Limpa o parâmetro da URL
  };

  if (authLoading || (searchParams.get("with_user") && loadingChat)) {
    return (
      <div className="flex h-full min-h-[80vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    );
  }

  if (!currentUser || !token) {
    return <div className="p-4 text-zinc-400">Faça login para ver suas mensagens.</div>;
  }

  // Se um usuário foi selecionado via URL, mostra o chat
  if (selectedUser) {
    return (
      <Chat
        otherUser={selectedUser}
        currentUserId={currentUser.id}
        token={token}
        onBack={handleBackToList}
      />
    );
  }

  // Se nenhum usuário foi selecionado, mostra a lista de conversas (placeholder)
  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold border-b border-zinc-800 pb-4">Mensagens Diretas</h1>
      <div className="flex flex-col items-center justify-center h-[60vh] text-zinc-500">
        <MessageSquare className="h-12 w-12 mb-4" />
        <p className="text-center">Selecione uma conversa para começar ou vá ao perfil de um usuário para enviar uma nova mensagem.</p>
      </div>
      {/* Futuramente, aqui você renderizaria o <ConversationList /> */}
    </div>
  );
}

/**
 * A página /direct precisa usar <Suspense> porque o componente DirectMessages
 * usa o hook `useSearchParams`, que depende do rendering do lado do cliente.
 */
export default function DirectPage() {
  return (
    <Suspense fallback={
      <div className="flex h-full min-h-[80vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
      </div>
    }>
      <DirectMessages />
    </Suspense>
  );
}