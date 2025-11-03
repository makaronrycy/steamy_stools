// src/components/Leaderboard.tsx
import React from "react";
import type { LeaderboardEntry } from "../types";

interface LeaderboardProps {
  entries: LeaderboardEntry[];
}

export const Leaderboard: React.FC<LeaderboardProps> = ({ entries }) => {
  return (
    <div className="leaderboard">
      <h3>🏆 Ranking graczy</h3>
      {entries.length === 0 ? (
        <p>Brak danych rankingowych</p>
      ) : (
        <ol className="leaderboard-list">
          {entries.map((entry, idx) => (
            <li key={idx} className="leaderboard-item">
              <span className="player-name">{entry.player}</span>
              <span className="player-score">{entry.score} pkt</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
};
