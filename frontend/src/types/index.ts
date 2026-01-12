// src/types/index.ts

/**
 * Reprezentuje wiadomość w czacie.
 */
export interface Message {
  /** Nadawca wiadomości (np. "Ty", "🤖 GPT", "Błąd") */
  sender: string;
  /** Treść wiadomości */
  content: string;
  /** Znacznik czasu wysłania */
  timestamp: Date;
}

/**
 * Wpis w tablicy wyników (leaderboard).
 */
export interface LeaderboardEntry {
  /** Nazwa gracza */
  player: string;
  /** Wynik punktowy */
  score: number;
}

/**
 * Odpowiedź z narzędzia otrzymana przez WebSocket.
 */
export interface ToolResponse {
  /** Typ wiadomości - zawsze "tool_response" */
  type: "tool_response";
  /** Nazwa narzędzia, które zwróciło odpowiedź */
  tool: string;
  /** Dane odpowiedzi */
  data: {
    /** Wynik operacji - tekst lub obiekt z leaderboardem */
    result?: string | { leaderboard?: LeaderboardEntry[]; total_players?: number };
    /** Komunikat błędu, jeśli wystąpił */
    error?: string;
  };
}

/**
 * Wiadomość aktualizacyjna otrzymana przez WebSocket.
 */
export interface UpdateMessage {
  /** Typ wiadomości - zawsze "update" */
  type: "update";
  /** Treść komunikatu aktualizacyjnego */
  message: string;
}

/**
 * Typ unii dla wszystkich wiadomości WebSocket.
 */
export type WebSocketMessage = ToolResponse | UpdateMessage;

