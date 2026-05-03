/**
 * ───────────────────────────────────────────────────────────────────────
 *  useChat – Hook WebSocket para mensagens em tempo real
 *  ───────────────────────────────────────────────────────────────────────
 *  Conecta ao endpoint /ws/chat do backend FastAPI.
 *
 *  Fluxo:
 *    1. Recebe o token JWT como parâmetro
 *    2. Conecta via ws://backend/ws/chat?token={token}
 *    3. Expõe callbacks: onMessage, onError
 *    4. Expõe função: sendMessage
 *    5. Reconexão automática com setTimeout em caso de queda
 *
 *  Uso típico:
 *    const ws = useChat({ token: "jwt..." });
 *    ws.onMessage((data) => console.log(data));
 *    ws.sendMessage(toUserId, "Olá!");
 * ───────────────────────────────────────────────────────────────────────
 */

"use client";

import { useRef, useState, useCallback, useEffect } from "react";

// ── Constantes ─────────────────────────────────────────────────────────
const RECONNECT_DELAY = 3_000; // 3s
const HEARTBEAT_INTERVAL = 25_000; // 25s

// ── Tipos ──────────────────────────────────────────────────────────────
export interface ChatMessageData {
  id: number;
  conversation_id: number;
  sender_id: number;
  content: string;
  media_url: string | null;
  created_at: string | null;
  all_read: boolean;
  is_mine: boolean;
}

interface WsPayload {
  type: string;
  [key: string]: unknown;
}

export interface UseChatOptions {
  /** Token JWT para autenticacao */
  token: string | null;
}

export interface UseChatReturn {
  /** True se o WebSocket esta conectado */
  connected: boolean;
  /** True se esta tentando reconectar */
  reconnecting: boolean;
  /** Callback disparado ao receber uma mensagem nova */
  onMessage: (handler: (msg: ChatMessageData) => void) => void;
  /** Callback disparado ao receber um erro do servidor */
  onError: (handler: (detail: string) => void) => void;
  /** Callback disparado ao receber confirmacao de leitura */
  onReadReceipt: (handler: (data: { conversation_id: number; message_ids: number[] }) => void) => void;
  /** Callback disparado ao receber ack de envio */
  onAck: (handler: (data: { message_id: number; conversation_id: number }) => void) => void;
  /** Envia uma mensagem de chat */
  sendMessage: (toUserId: number, content: string) => boolean;
  /** Envia confirmacao de leitura */
  sendReadReceipt: (conversationId: number) => void;
  /** Desconecta manualmente */
  disconnect: () => void;
}

// ── Hook ───────────────────────────────────────────────────────────────
export function useChat(options: UseChatOptions): UseChatReturn {
  const { token } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  // Callbacks armazenados em refs para nao recriar o hook
  const onMessageRef = useRef<((msg: ChatMessageData) => void) | null>(null);
  const onErrorRef = useRef<((detail: string) => void) | null>(null);
  const onReadReceiptRef = useRef<((data: { conversation_id: number; message_ids: number[] }) => void) | null>(null);
  const onAckRef = useRef<((data: { message_id: number; conversation_id: number }) => void) | null>(null);

  // ── Helpers de registro de callback ─────────────────────────────────
  const onMessage = useCallback((handler: (msg: ChatMessageData) => void) => {
    onMessageRef.current = handler;
  }, []);

  const onError = useCallback((handler: (detail: string) => void) => {
    onErrorRef.current = handler;
  }, []);

  const onReadReceipt = useCallback(
    (handler: (data: { conversation_id: number; message_ids: number[] }) => void) => {
      onReadReceiptRef.current = handler;
    },
    []
  );

  const onAck = useCallback(
    (handler: (data: { message_id: number; conversation_id: number }) => void) => {
      onAckRef.current = handler;
    },
    []
  );

  // ── Heartbeat ───────────────────────────────────────────────────────
  const startHeartbeat = useCallback((ws: WebSocket) => {
    stopHeartbeat();
    heartbeatRef.current = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, HEARTBEAT_INTERVAL);
  }, []);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  // ── Conectar ────────────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (!token || !mountedRef.current) return;

    // Limpa conexao anterior
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Determina URL base do WebSocket
    const wsBase =
      process.env.NEXT_PUBLIC_WS_URL ||
      (typeof window !== "undefined"
        ? `ws://${window.location.hostname}:8000`
        : "ws://localhost:8000");

    const url = `${wsBase}/api/chat/ws?token=${token}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) {
        ws.close();
        return;
      }
      setConnected(true);
      setReconnecting(false);
      startHeartbeat(ws);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (!mountedRef.current) return;

      try {
        const data: WsPayload = JSON.parse(event.data);

        switch (data.type) {
          case "new_message":
            onMessageRef.current?.(data.message as unknown as ChatMessageData);
            break;

          case "read_receipt":
            onReadReceiptRef.current?.({
              conversation_id: data.conversation_id as number,
              message_ids: data.message_ids as number[],
            });
            break;

          case "ack":
            onAckRef.current?.({
              message_id: data.message_id as number,
              conversation_id: data.conversation_id as number,
            });
            break;

          case "error":
            onErrorRef.current?.(data.detail as string);
            break;

          case "connected":
          case "pong":
            // Heartbeat / conexao estabelecida
            break;

          default:
            break;
        }
      } catch {
        // Ignora mensagens mal formatadas
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnected(false);
      stopHeartbeat();
      scheduleReconnect();
    };

    ws.onerror = () => {
      // onclose sera chamado em seguida
    };
  }, [token, startHeartbeat, stopHeartbeat]);

  // ── Reconexao ───────────────────────────────────────────────────────
  const scheduleReconnect = useCallback(() => {
    if (reconnectRef.current) return;
    setReconnecting(true);
    reconnectRef.current = setTimeout(() => {
      reconnectRef.current = null;
      if (mountedRef.current) {
        connect();
      }
    }, RECONNECT_DELAY);
  }, [connect]);

  // ── Enviar mensagem ─────────────────────────────────────────────────
  const sendMessage = useCallback((toUserId: number, content: string): boolean => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "message", to: toUserId, content }));
      return true;
    }
    return false; // Nao conectado -> usar fallback REST
  }, []);

  // ── Enviar confirmacao de leitura ───────────────────────────────────
  const sendReadReceipt = useCallback((conversationId: number) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "read", conversation_id: conversationId }));
    }
  }, []);

  // ── Desconectar ─────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    mountedRef.current = false;
    stopHeartbeat();
    if (reconnectRef.current) {
      clearTimeout(reconnectRef.current);
      reconnectRef.current = null;
    }
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
    setReconnecting(false);
  }, [stopHeartbeat]);

  // ── Efeito: montar/desmontar ───────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    if (token) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [token, connect, disconnect]);

  return {
    connected,
    reconnecting,
    onMessage,
    onError,
    onReadReceipt,
    onAck,
    sendMessage,
    sendReadReceipt,
    disconnect,
  };
}