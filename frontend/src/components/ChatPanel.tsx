// src/components/ChatPanel.tsx
import React, { useState, useRef, useEffect } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import type { Message } from "../types";
import { api } from "../services/api";

interface ChatPanelProps {
  messages: Message[];
  onMessageAdded: (message: Message) => void;
  userId: string;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onMessageAdded, userId }) => {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const hasFetchedInitial = useRef(false); // Prevent double fetch in StrictMode

  // Speech recognition hook
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-trigger agent's first message when component mounts
  useEffect(() => {
    const fetchInitialGreeting = async () => {
      if (hasFetchedInitial.current) return; // Prevent double fetch
      if (messages.length === 0 && !isLoading) {
        hasFetchedInitial.current = true;
        setIsLoading(true);
        try {
          // Send empty/init message to get agent to start conversation
          const response = await api.sendToLLM("", userId);
          const botMessage: Message = {
            sender: "🤖 GPT",
            content: response,
            timestamp: new Date(),
          };
          onMessageAdded(botMessage);
        } catch (error) {
          console.error("Failed to get initial greeting:", error);
          hasFetchedInitial.current = false; // Allow retry on error
        } finally {
          setIsLoading(false);
        }
      }
    };
    fetchInitialGreeting();
  }, []); // Run only once on mount

  // Update input when transcript changes
  useEffect(() => {
    if (transcript) {
      setInput(transcript);
    }
  }, [transcript]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    // Stop listening if active
    if (listening) {
      SpeechRecognition.stopListening();
    }

    const userMessage: Message = {
      sender: "Ty",
      content: input,
      timestamp: new Date(),
    };

    onMessageAdded(userMessage);
    setInput("");
    resetTranscript();
    setIsLoading(true);

    try {
      const response = await api.sendToLLM(input, userId);
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

  const toggleListening = () => {
    if (listening) {
      SpeechRecognition.stopListening();
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: true, language: "pl-PL" });
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
          placeholder={listening ? "🎤 Słucham..." : "Wpisz wiadomość..."}
          disabled={isLoading}
        />
        {browserSupportsSpeechRecognition && (
          <button
            onClick={toggleListening}
            disabled={isLoading}
            className={listening ? "btn-mic-active" : "btn-mic"}
            title={listening ? "Zatrzymaj nagrywanie" : "Rozpocznij nagrywanie głosowe"}
          >
            {listening ? "🔴" : "🎤"}
          </button>
        )}
        <button onClick={handleSend} disabled={isLoading}>
          {isLoading ? "⏳" : "📤"} Wyślij
        </button>
      </div>
      {!browserSupportsSpeechRecognition && (
        <p className="speech-warning">⚠️ Twoja przeglądarka nie wspiera rozpoznawania mowy.</p>
      )}
    </div>
  );
};
