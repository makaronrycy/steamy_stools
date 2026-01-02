import { useState, useEffect } from "react";
import "./App.css";
import { ChatPanel } from "./components/ChatPanel";
import { AdminPanel } from "./components/AdminPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import type { Message } from "./types";

const WS_URL = `ws://${location.hostname}:8000/ws`;

function App() {
  const { isConnected, connect } = useWebSocket(WS_URL);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  const handleMessageAdded = (m: Message) => setChatMessages((p) => [...p, m]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Wywiad – Gorące Krzesła</h1>
      </header>

      <div className="main-content two-columns">
        <div className="left-column">
          {/* QuestionCard removed as per request */}
          <ChatPanel messages={chatMessages} onMessageAdded={handleMessageAdded} />
        </div>
        <div className="right-column">
          <AdminPanel />
        </div>
      </div>

      <footer className="app-footer">
        <span className={isConnected ? "status-connected" : "status-disconnected"}>
          {isConnected ? "🟢 Połączono z WebSocket" : "🔴 Rozłączono"}
        </span>
      </footer>
    </div>
  );
}

export default App;
