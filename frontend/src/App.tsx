import { useState, useEffect, useCallback } from "react";
import "./App.css";
import { ControlBar } from "./components/ControlBar";
import { QuestionCard } from "./components/QuestionCard";
import { ChatPanel } from "./components/ChatPanel";
import { AdminPanel } from "./components/AdminPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import type { Message, ToolResponse } from "./types";

const WS_URL = `ws://${location.hostname}:8000/ws`;

function App() {
  const { isConnected, messages: wsMessages, connect, disconnect, send } = useWebSocket(WS_URL);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [chatMessages, setChatMessages] = useState<Message[]>([]);

  useEffect(() => {
    const last = wsMessages.at(-1);
    if (!last) return;
    if (last.type === "tool_response") {
      const tr = last as ToolResponse;
      if (tr.data.error) {
        setChatMessages((p) => [...p, { sender: "Błąd", content: tr.data.error!, timestamp: new Date() }]);
        return;
      }
      if (tr.tool === "get_random_question" && typeof tr.data.result === "string") {
        setCurrentQuestion(tr.data.result);
        setChatMessages((p) => [...p, { sender: "System", content: `Nowe pytanie: ${tr.data.result}`, timestamp: new Date() }]);
      }
    }
  }, [wsMessages]);

  const handleNextQuestion = useCallback(() => {
    send({ tool: "get_random_question", arguments: {} });
  }, [send]);

  const handleGenerateResults = useCallback(() => {
    setChatMessages((p) => [...p, { sender: "Admin", content: "Generacja wyników – w przygotowaniu", timestamp: new Date() }]);
  }, []);

  const handleAnalyzeGithub = useCallback(() => {
    setChatMessages((p) => [...p, { sender: "Admin", content: "Analiza GitHuba – w przygotowaniu", timestamp: new Date() }]);
  }, []);

  const handleMessageAdded = (m: Message) => setChatMessages((p) => [...p, m]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎤 Wywiad – Gorące Krzesła</h1>
        <p className="subtitle">MCP + WebSocket + LLM</p>
      </header>

      <ControlBar
        isConnected={isConnected}
        onConnect={connect}
        onDisconnect={disconnect}
        onNextQuestion={handleNextQuestion}
      />

      <div className="main-content two-columns">
        <div className="left-column">
          <QuestionCard question={currentQuestion} />
          <ChatPanel messages={chatMessages} onMessageAdded={handleMessageAdded} />
        </div>
        <div className="right-column">
          <AdminPanel
            onGenerateResults={handleGenerateResults}
            onAnalyzeGithub={handleAnalyzeGithub}
            disabled={!isConnected}
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
