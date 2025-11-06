// src/types/index.ts
export interface Message {
  sender: string;
  content: string;
  timestamp: Date;
}

export interface LeaderboardEntry {
  player: string;
  score: number;
}

export interface ToolResponse {
  type: "tool_response";
  tool: string;
  data: {
    result?: string | { leaderboard?: LeaderboardEntry[]; total_players?: number };
    error?: string;
  };
}

export interface UpdateMessage {
  type: "update";
  message: string;
}

export type WebSocketMessage = ToolResponse | UpdateMessage;
