// src/components/AdminPanel.tsx
import React, { useState } from "react";
import { api } from "../services/api";

export const AdminPanel: React.FC = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [message, setMessage] = useState<string>("");
  const [messageType, setMessageType] = useState<"success" | "error" | "info">("info");

  const handleGithubAnalysis = async () => {
    setIsAnalyzing(true);
    setMessage("Rozpoczynanie analizy GitHub...");
    setMessageType("info");

    try {
      const result = await api.analyzeGithub();
      setMessage(result.message || "Analiza została uruchomiona pomyślnie!");
      setMessageType("success");
      
      console.log("GitHub Analysis Result:", result);
    } catch (error: any) {
      setMessage(
        error.response?.data?.message || 
        error.message || 
        "Wystąpił błąd podczas uruchamiania analizy"
      );
      setMessageType("error");
      console.error("GitHub Analysis Error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const checkStatus = async () => {
    try {
      const status = await api.getGithubAnalysisStatus();
      setMessage(status.message || "Status sprawdzony");
      setMessageType("info");
      console.log("GitHub Analysis Status:", status);
    } catch (error: any) {
      setMessage("Nie można sprawdzić statusu analizy");
      setMessageType("error");
      console.error("Status Check Error:", error);
    }
  };

  return (
    <div className="admin-panel">
      <h2>Panel Administratora</h2>
      
      <div className="admin-section">
        <h3>🔍 Analiza GitHub</h3>
        <p>Uruchom pełną analizę repozytorium GitHub z metrykami kodu i regularności commitów.</p>
        
        <div className="button-group">
          <button
            onClick={handleGithubAnalysis}
            disabled={isAnalyzing}
            className={isAnalyzing ? "btn-primary btn-disabled" : "btn-primary"}
          >
            {isAnalyzing ? "⏳ Analizuję..." : "🚀 Uruchom analizę GitHub"}
          </button>
          
          <button
            onClick={checkStatus}
            disabled={isAnalyzing}
            className="btn-secondary"
          >
            📊 Sprawdź status
          </button>
        </div>

        {message && (
          <div className={`message message-${messageType}`}>
            {messageType === "success" && "✅ "}
            {messageType === "error" && "❌ "}
            {messageType === "info" && "ℹ️ "}
            {message}
          </div>
        )}
      </div>

      <div className="admin-info">
        <h4>ℹ️ Informacje</h4>
        <ul>
          <li>Analiza może potrwać kilka minut w zależności od wielkości repozytorium</li>
          <li>Wyniki zostaną zapisane w bazie danych MongoDB</li>
          <li>Analiza obejmuje: metryki kodu, wykrywanie niepotrzebnych commitów, regularność</li>
          <li>Upewnij się, że SonarQube jest uruchomiony przed analizą</li>
        </ul>
      </div>
    </div>
  );
};