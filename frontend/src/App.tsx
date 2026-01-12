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
  const normalizePath = (path: string) => path.replace(/\/+$/, "") || "/";
  const isAdminPath = (loc: Location) => {
    const pathname = normalizePath(loc.pathname);
    const hashPath = loc.hash.replace(/^#/, "");
    return pathname === "/admin" || normalizePath(hashPath) === "/admin";
  };
  const [isAdminRoute, setIsAdminRoute] = useState(() => isAdminPath(window.location));

  // User selection state
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);

  // Auto-connect on mount
  useEffect(() => {
    connect();
  }, [connect]);

  useEffect(() => {
    const handleRouteChange = () => setIsAdminRoute(isAdminPath(window.location));
    window.addEventListener("popstate", handleRouteChange);
    window.addEventListener("hashchange", handleRouteChange);
    return () => {
      window.removeEventListener("popstate", handleRouteChange);
      window.removeEventListener("hashchange", handleRouteChange);
    };
  }, []);

  const handleMessageAdded = (m: Message) => setChatMessages((p) => [...p, m]);

  const handleUserSelect = (id: string, name: string) => {
    setUserId(id);
    setUserName(name);
  };

  if (isAdminRoute) {
    return (
      <div className="app flex flex-col items-center justify-center bg-gray-900 min-h-screen gap-6 p-6">
        {!isAdminUnlocked && (
          <div className="w-full max-w-md">
            <AdminAccess
              onAccessGranted={() => {
                setIsAdminUnlocked(true);
                setShowAdminAccess(false);
              }}
            />
          </div>
        )}

        {isAdminUnlocked && (
          <div className="w-full max-w-5xl">
            <AdminPanel />
          </div>
        )}
      </div>
    );
  }

  if (!userId) {
    return (
      <div className="app flex flex-col items-center justify-center bg-gray-900 min-h-screen gap-6 p-6">
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
      </header>

      <div className={`main-content ${isAdminUnlocked ? 'two-columns' : 'single-column'}`}>
        <div className="left-column">
          <ChatPanel
            messages={chatMessages}
            onMessageAdded={handleMessageAdded}
            userId={userId}
          />
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
