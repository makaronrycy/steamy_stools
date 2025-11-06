// src/services/api.ts
import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

export const api = {
  async sendToLLM(message: string): Promise<string> {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/llm`, {
        message,
      });
      return response.data.response;
    } catch (error) {
      console.error("LLM API error:", error);
      throw error;
    }
  },

  async healthCheck(): Promise<boolean> {
    try {
      const response = await axios.get(`${API_BASE_URL}/health`);
      return response.data.status === "ok";
    } catch (error) {
      return false;
    }
  },

  // === GitHub Analysis ===
  async analyzeGithub(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/github/analyze`);
      return response.data;
    } catch (error) {
      console.error("GitHub analysis error:", error);
      throw error;
    }
  },

  async getGithubAnalysisStatus(): Promise<{ status: string; message: string }> {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/github/status`);
      return response.data;
    } catch (error) {
      console.error("GitHub status error:", error);
      throw error;
    }
  },
};