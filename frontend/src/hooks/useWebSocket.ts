// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState, useCallback } from "react";
import type { WebSocketMessage } from "../types";

/**
 * Hook do zarządzania połączeniem WebSocket.
 * Zapewnia automatyczne ponowne łączenie po rozłączeniu.
 * 
 * @param url - Adres URL serwera WebSocket
 * @returns Obiekt z metodami i stanem połączenia:
 *   - isConnected: czy połączenie jest aktywne
 *   - messages: tablica odebranych wiadomości
 *   - connect: funkcja do nawiązania połączenia
 *   - disconnect: funkcja do rozłączenia
 *   - send: funkcja do wysyłania danych
 */
export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);

  /**
   * Nawiązuje połączenie WebSocket.
   * Automatycznie próbuje ponownie połączyć po 3 sekundach w przypadku rozłączenia.
   */
  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log("✅ WebSocket connected");
        setIsConnected(true);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          setMessages((prev) => [...prev, data]);
        } catch (err) {
          console.error("Failed to parse message:", err);
        }
      };

      ws.current.onerror = (error) => {
        console.error("❌ WebSocket error:", error);
      };

      ws.current.onclose = () => {
        console.log("🔴 WebSocket disconnected");
        setIsConnected(false);

        // Auto-reconnect po 3 sekundach
        reconnectTimeout.current = window.setTimeout(() => {
          console.log("🔄 Attempting to reconnect...");
          connect();
        }, 3000);
      };
    } catch (err) {
      console.error("Connection failed:", err);
    }
  }, [url]);

  /**
   * Rozłącza połączenie WebSocket.
   * Anuluje również zaplanowane próby ponownego połączenia.
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
    }
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
  }, []);

  /**
   * Wysyła dane przez połączenie WebSocket.
   * Dane są automatycznie serializowane do JSON.
   * 
   * @param data - Obiekt do wysłania
   */
  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data));
    } else {
      console.warn("WebSocket is not connected");
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { isConnected, messages, connect, disconnect, send };
};
