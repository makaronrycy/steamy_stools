// src/App.tsx
import { useState, useEffect } from "react";
import "./App.css";
import { useWebSocket } from "./hooks/useWebSocket";
import { ControlBar } from "./components/ControlBar";
import { QuestionCard } from "./components/QuestionCard";
import { ChatPanel } from "./components/ChatPanel";
import { Leaderboard } from "./components/Leaderboard";
import type { Message, LeaderboardEntry, ToolResponse } from "./types";

const WS_URL = "ws://localhost:8000/ws";

function App() {
  const { isConnected, messages: wsMessages, connect, disconnect, send } = useWebSocket(WS_URL);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);

  // Obsługa wiadomości WebSocket
  useEffect(() => {
    const lastMessage = wsMessages[wsMessages.length - 1];
    if (!lastMessage) return;

    if (lastMessage.type === "tool_response") {
      const toolResponse = lastMessage as ToolResponse;
      const { tool, data } = toolResponse;

      if (data.error) {
        console.error(`Błąd narzędzia ${tool}:`, data.error);
        return;
      }

      if (tool === "get_random_question" && typeof data.result === "string") {
        setCurrentQuestion(data.result);
        const sysMessage: Message = {
          sender: "System",
          content: `Nowe pytanie: ${data.result}`,
          timestamp: new Date(),
        };
        setChatMessages((prev) => [...prev, sysMessage]);
      }

      if (tool === "get_leaderboard" && typeof data.result === "object") {
        const leaderboardData = data.result as { leaderboard?: LeaderboardEntry[] };
        if (leaderboardData.leaderboard) {
          setLeaderboard(leaderboardData.leaderboard);
        }
      }
    }

    if (lastMessage.type === "update") {
      console.log("📡 Update:", lastMessage.message);
    }
  }, [wsMessages]);

  const handleGetQuestion = () => {
    send({ tool: "get_random_question", arguments: {} });
  };

  const handleGetLeaderboard = () => {
    send({ tool: "get_leaderboard", arguments: {} });
  };

  const handleMessageAdded = (message: Message) => {
    setChatMessages((prev) => [...prev, message]);
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎮 Gorące Krzesła</h1>
        <p className="subtitle">Gra z integracją AI (MCP + GPT)</p>
      </header>

      <ControlBar
        isConnected={isConnected}
        onConnect={connect}
        onDisconnect={disconnect}
        onGetQuestion={handleGetQuestion}
        onGetLeaderboard={handleGetLeaderboard}
      />

      <div className="main-content">
        <div className="left-column">
          <QuestionCard question={currentQuestion} />
          <ChatPanel messages={chatMessages} onMessageAdded={handleMessageAdded} />
        </div>
        <div className="right-column">
          <Leaderboard entries={leaderboard} />
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
