// src/components/ChatPanel.tsx
import React, { useState, useRef, useEffect } from "react";
import type { Message } from "../types";
import { api } from "../services/api";

interface ChatPanelProps {
  messages: Message[];
  onMessageAdded: (message: Message) => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onMessageAdded }) => {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      sender: "Ty",
      content: input,
      timestamp: new Date(),
    };

    onMessageAdded(userMessage);
    setInput("");
    setIsLoading(true);

    try {
      const response = await api.sendToLLM(input);
      const botMessage: Message = {
        sender: "🤖 GPT",
        content: response,
        timestamp: new Date(),
      };
      onMessageAdded(botMessage);
    } catch (error) {
      const errorMessage: Message = {
        sender: "Błąd",
        content: "Nie udało się połączyć z LLM",
        timestamp: new Date(),
      };
      onMessageAdded(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-panel">
      <h3>💬 Czat z LLM (GPT):</h3>
      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className="chat-message">
            <strong>{msg.sender}:</strong> {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          placeholder="Wpisz wiadomość..."
          disabled={isLoading}
        />
        <button onClick={handleSend} disabled={isLoading}>
          {isLoading ? "⏳" : "📤"} Wyślij
        </button>
      </div>
    </div>
  );
};
