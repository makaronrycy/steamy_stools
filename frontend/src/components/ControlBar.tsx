// src/components/ControlBar.tsx
import React from "react";

interface ControlBarProps {
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onGetQuestion: () => void;
  onGetLeaderboard: () => void;
}

export const ControlBar: React.FC<ControlBarProps> = ({
  isConnected,
  onConnect,
  onDisconnect,
  onGetQuestion,
  onGetLeaderboard,
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
        onClick={onGetQuestion}
        disabled={!isConnected}
        className="btn-info"
      >
        🎲 Losuj pytanie
      </button>
      <button
        onClick={onGetLeaderboard}
        disabled={!isConnected}
        className="btn-warning"
      >
        🏆 Ranking
      </button>
    </div>
  );
};
