// src/services/api.ts
import axios from "axios";

const API_BASE_URL = "http://localhost:8000";     // Twój FastAPI backend
const DOCKER_AGENT_URL = "http://localhost:3000"; // agent-client w Dockerze

export const api = {
  // === ChatPanel -> Docker MCP agent (Docker) ===
  async sendToLLM(message: string): Promise<string> {
    try {
      // Docelowo user_id możesz brać z logowania / stanu, na razie na sztywno
      const user_id = "2001";

      const payload = {
        user_id,
        answer: message,          // dokładnie tak samo jak w test_script.py (poprawiono typo)
        question_target: "general",
      };

      const response = await axios.post(
        `${DOCKER_AGENT_URL}/start_agent`,
        payload,
        {
          headers: { "Content-Type": "application/json" },
        }
      );

      // Backend zwraca: { status, question, next_state, current_state }
      const data = response.data;
      return data.question ?? "Brak odpowiedzi od agenta.";
    } catch (error) {
      console.error("LLM (Docker MCP) API error:", error);
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
};
