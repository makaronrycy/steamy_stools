// src/services/api.ts
import axios from "axios";

// Dynamic URLs - work both in Docker and local development
const API_BASE_URL = import.meta.env.VITE_BACKEND_URL || `http://${location.hostname}:8000`;

export const api = {
  // === ChatPanel -> Backend proxy -> Agent Client ===
  async sendToLLM(message: string): Promise<string> {
    try {
      // user_id możesz brać z logowania / stanu, na razie na sztywno
      const user_id = "2001";

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

  // === Pozostałe funkcje jak wcześniej (FastAPI na :8000) ===
  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data.status === "ok";
    } catch {
      return false;
    }
  },

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
};
