// src/components/ControlBar.tsx
import React from "react";

interface ControlBarProps {
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  onNextQuestion: () => void;
}

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
