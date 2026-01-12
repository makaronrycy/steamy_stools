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

  const handleInitDatabase = async () => {
    setIsAnalyzing(true);
    setMessage("Inicjalizowanie bazy danych...");
    setMessageType("info");

    try {
      const result = await api.initDatabase();

      if (result.status === "success") {
        setMessage(result.message || "Baza danych zainicjalizowana pomyślnie!");
        setMessageType("success");
      } else {
        setMessage(result.message || "Błąd podczas inicjalizacji bazy.");
        setMessageType("error");
      }

      console.log("DB Init Result:", result);
    } catch (error: any) {
      setMessage("Nie udało się zainicjalizować bazy danych.");
      setMessageType("error");
      console.error("DB Init Error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };


  const handleAssumptionsInit = async () => {
    setIsAnalyzing(true);
    setMessage("Tworzenie katalogów założeń...");
    setMessageType("info");

    try {
      const result = await api.initAssumptions(); // Assuming this is added to api.ts

      if (result.status === "success") {
        setMessage(result.message || "Katalogi zostały utworzone.");
        setMessageType("success");
      } else {
        setMessage(result.message || "Błąd podczas tworzenia katalogów.");
        setMessageType("error");
      }
    } catch (error: any) {
      setMessage("Nie udało się utworzyć katalogów.");
      setMessageType("error");
      console.error("Assumptions Init Error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };


  const handleAssumptionsAnalyze = async () => {
    setIsAnalyzing(true);
    setMessage("Trwa analiza założeń (może to zająć chwilę)...");
    setMessageType("info");

    try {
      const result = await api.analyzeAssumptions();

      if (result.status === "success") {
        setMessage(result.message || "Analiza zakończona.");
        setMessageType("success");
      } else {
        setMessage(result.message || "Błąd podczas analizy.");
        setMessageType("error");
      }
    } catch (error: any) {
      setMessage("Nie udało się przeprowadzić analizy.");
      setMessageType("error");
      console.error("Assumptions Analyze Error:", error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGenerateReports = async () => {
    setIsAnalyzing(true);
    setMessage("Generowanie raportów (może to potrwać kilka minut)...");
    setMessageType("info");

    try {
      const result = await api.generateReports();

      if (result.status === "success") {
        setMessage(result.message || "Raporty zostały wygenerowane pomyślnie!");
        setMessageType("success");
      } else {
        setMessage(result.message || "Błąd podczas generowania raportów.");
        setMessageType("error");
      }
    } catch (error: any) {
      setMessage("Nie udało się wygenerować raportów.");
      setMessageType("error");
      console.error("Reports Generation Error:", error);
    } finally {
      setIsAnalyzing(false);
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
            onClick={handleInitDatabase}
            disabled={isAnalyzing}
            className="btn-secondary"
            style={{ marginLeft: "10px", backgroundColor: "#2ecc71" }}
          >
            🗄️ Inicjalizuj Bazę Danych
          </button>
        </div>

        <div style={{ marginTop: "20px" }}>
          <h4>📁 Zarządzanie Założeniami</h4>
          <div className="button-group">
            <button
              onClick={handleAssumptionsInit}
              disabled={isAnalyzing}
              className="btn-secondary"
              style={{ backgroundColor: "#e67e22" }}
            >
              1. Utwórz Katalogi
            </button>

            <button
              onClick={handleAssumptionsAnalyze}
              disabled={isAnalyzing}
              className="btn-primary"
              style={{ marginLeft: "10px", backgroundColor: "#9b59b6" }}
            >
              2. Uruchom Analizę Założeń
            </button>
          </div>
        </div>

        <div style={{ marginTop: "20px" }}>
          <h4>📊 Generowanie Raportów</h4>
          <p style={{ fontSize: "14px", opacity: 0.8 }}>
            Generuje raporty CSV z ocenami i statystykami z bazy Neo4j.
          </p>
          <div className="button-group">
            <button
              onClick={handleGenerateReports}
              disabled={isAnalyzing}
              className="btn-primary"
              style={{ backgroundColor: "#3498db" }}
            >
              📄 Generuj Raporty CSV
            </button>
          </div>
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