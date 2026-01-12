// src/services/api.ts
import axios from "axios";

// Dynamic URLs - work both in Docker and local development
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || `http://${location.hostname}:8000`;

export const api = {
  /**
   * Wysyła wiadomość do LLM (Agent) poprzez proxy backendu.
   * 
   * @param message - Treść wiadomości do wysłania
   * @param userId - ID użytkownika (domyślnie "2001")
   * @returns Odpowiedź od agenta LLM
   * @throws Error gdy API zwróci błąd lub połączenie nie powiedzie się
   */
  async sendToLLM(message: string, userId: string = "2001"): Promise<string> {
    try {
      // user_id przekazany dynamicznie
      const user_id = userId;

      const payload = {
        user_id,
        answer: message,
        question_target: "general",
      };

      // Używamy proxy przez backend (CORS bypass)
      const response = await axios.post(
        `${API_BASE_URL}/api/agent/start`,
        payload,
        {
          headers: { "Content-Type": "application/json" },
          timeout: 300000, // 5 minut timeout
        }
      );

      // Backend zwraca: { status, question, next_state, current_state }
      const data = response.data;

      if (data.error) {
        throw new Error(data.message || data.error);
      }

      return data.question ?? "Brak odpowiedzi od agenta.";
    } catch (error) {
      console.error("LLM (Agent) API error:", error);
      throw error;
    }
  },

  /**
   * Sprawdza stan zdrowia backendu (health check).
   * 
   * @returns true jeśli backend działa poprawnie, false w przeciwnym przypadku
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data.status === "ok";
    } catch {
      return false;
    }
  },

  /**
   * Uruchamia analizę repozytorium GitHub.
   * Analiza obejmuje metryki kodu, wykrywanie niepotrzebnych commitów i regularność.
   * 
   * @returns Status operacji i komunikat
   * @throws Error gdy analiza nie powiedzie się
   */
  async analyzeGithub(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/github/analyze`
      );
      return response.data;
    } catch (error) {
      console.error("GitHub analysis error:", error);
      throw error;
    }
  },

  /**
   * Pobiera aktualny status analizy GitHub.
   * 
   * @returns Status analizy i komunikat
   * @throws Error gdy nie można pobrać statusu
   */
  async getGithubAnalysisStatus(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/github/status`
      );
      return response.data;
    } catch (error) {
      console.error("GitHub status error:", error);
      throw error;
    }
  },

  /**
   * Inicjalizuje bazę danych Neo4j.
   * Tworzy niezbędne węzły i relacje w grafowej bazie danych.
   * 
   * @returns Status operacji i komunikat
   * @throws Error gdy inicjalizacja nie powiedzie się
   */
  async initDatabase(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/neo4j/init`
      );
      return response.data;
    } catch (error) {
      console.error("Database init error:", error);
      throw error;
    }
  },

  /**
   * Inicjalizuje katalogi założeń projektowych.
   * Tworzy strukturę katalogów dla każdego projektu.
   * 
   * @returns Status operacji i komunikat
   * @throws Error gdy nie można utworzyć katalogów
   */
  async initAssumptions(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/assumptions/init`
      );
      return response.data;
    } catch (error) {
      console.error("Assumptions init error:", error);
      throw error;
    }
  },

  /**
   * Uruchamia analizę założeń projektowych.
   * Przetwarza pliki założeń i zapisuje wyniki w bazie danych.
   * 
   * @returns Status operacji, komunikat oraz opcjonalna lista błędów
   * @throws Error gdy analiza nie powiedzie się
   */
  async analyzeAssumptions(): Promise<{ status: string; message: string; errors?: string[] }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/assumptions/analyze`
      );
      return response.data;
    } catch (error) {
      console.error("Assumptions analysis error:", error);
      throw error;
    }
  },

  /**
   * Pobiera listę osób (użytkowników) z serwera agenta.
   * Zwraca projekty z przypisanymi osobami.
   * 
   * @returns Tablica projektów z osobami lub pusta tablica w przypadku błędu
   */
  async getPeople(): Promise<any[]> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/agent/people`);
      return response.data;
    } catch (error) {
      console.error("Failed to fetch people:", error);
      return [];
    }
  },

  /**
   * Generuje raporty CSV z ocenami i statystykami.
   * Pobiera dane z bazy Neo4j i tworzy pliki raportów.
   * Operacja może potrwać kilka minut.
   * 
   * @returns Status operacji i komunikat
   * @throws Error gdy generowanie raportów nie powiedzie się
   */
  async generateReports(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/reports/generate`,
        {},
        { timeout: 300000 } // 5 minutes timeout
      );
      return response.data;
    } catch (error) {
      console.error("Reports generation error:", error);
      throw error;
    }
  },
};
