import { useState, useEffect } from "react";
import "./App.css";
import { ChatPanel } from "./components/ChatPanel";
import { AdminPanel } from "./components/AdminPanel";
import { AdminAccess } from "./components/AdminAccess";
import UserSelector from "./components/UserSelector";
import { useWebSocket } from "./hooks/useWebSocket";
import type { Message } from "./types";

const WS_URL = import.meta.env.VITE_BACKEND_URL
  ? `ws://${new URL(import.meta.env.VITE_BACKEND_URL).host}/ws`
  : `ws://${location.hostname}:8000/ws`;

function App() {
  const { isConnected, connect } = useWebSocket(WS_URL);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [isAdminUnlocked, setIsAdminUnlocked] = useState(false);
  const [showAdminAccess, setShowAdminAccess] = useState(false);

  // User selection state
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  const handleMessageAdded = (m: Message) => setChatMessages((p) => [...p, m]);

  const handleUserSelect = (id: string, name: string) => {
    setUserId(id);
    setUserName(name);
  };

  if (!userId) {
    return (
      <div className="app flex items-center justify-center bg-gray-900 min-h-screen">
        <UserSelector onSelect={handleUserSelect} />
      </div>
    );
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Wywiad – Gorące Krzesła</h1>
        <div className="subtitle">
          Zalogowany jako: {userName} ({userId})
        </div>
        {!isAdminUnlocked && (
          <button
            className="btn-admin-header"
            onClick={() => setShowAdminAccess(true)}
          >
            🔐 Panel Administratora
          </button>
        )}
      </header>

      {/* Modal dostępu do admina */}
      {showAdminAccess && !isAdminUnlocked && (
        <div className="admin-access-overlay" onClick={() => setShowAdminAccess(false)}>
          <div onClick={(e) => e.stopPropagation()}>
            <AdminAccess
              onAccessGranted={() => {
                setIsAdminUnlocked(true);
                setShowAdminAccess(false);
              }}
            />
          </div>
        </div>
      )}

      <div className={`main-content ${isAdminUnlocked ? 'two-columns' : 'single-column'}`}>
        <div className="left-column">
          <ChatPanel
            messages={chatMessages}
            onMessageAdded={handleMessageAdded}
            userId={userId}
          />
        </div>
        {isAdminUnlocked && (
          <div className="right-column">
            <AdminPanel />
          </div>
        )}
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

