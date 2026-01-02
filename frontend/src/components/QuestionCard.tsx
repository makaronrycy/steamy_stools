// src/components/QuestionCard.tsx
import React from "react";

interface QuestionCardProps {
  question: string;
}

export const QuestionCard: React.FC<QuestionCardProps> = ({ question }) => {
  return (
    <div className="question-card">
      <h3>❓ Aktualne pytanie:</h3>
      <p className="question-text">{question || "Kliknij 'Losuj pytanie' aby rozpocząć"}</p>
    </div>
  );
};
