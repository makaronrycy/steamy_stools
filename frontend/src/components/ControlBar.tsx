// src/components/ControlBar.tsx
import React from "react";

/**
 * Interfejs props dla komponentu ControlBar.
 */
interface ControlBarProps {
  /** Czy połączenie WebSocket jest aktywne */
  isConnected: boolean;
  /** Callback do nawiązania połączenia */
  onConnect: () => void;
  /** Callback do rozłączenia */
  onDisconnect: () => void;
  /** Callback do przejścia do następnego pytania */
  onNextQuestion: () => void;
}

/**
 * Pasek kontrolny z przyciskami do zarządzania połączeniem WebSocket
 * i nawigacji między pytaniami w wywiadzie.
 * 
 * @param props - Props komponentu
 */
export const ControlBar: React.FC<ControlBarProps> = ({
  isConnected,
  onConnect,
  onDisconnect,
  onNextQuestion,
}) => {
  return (
    <div className="control-bar">
      <button
        onClick={isConnected ? onDisconnect : onConnect}
        className={isConnected ? "btn-success" : "btn-primary"}
      >
        {isConnected ? "🟢 Połączono" : "🔌 Połącz WS"}
      </button>

      <button
        onClick={onNextQuestion}
        disabled={!isConnected}
        className="btn-info"
        title="Następne pytanie w wywiadzie"
      >
        🎯 Następne pytanie w wywiadzie
      </button>
    </div>
  );
};
