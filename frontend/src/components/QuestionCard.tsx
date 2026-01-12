// src/components/QuestionCard.tsx
import React from "react";

/**
 * Interfejs props dla komponentu QuestionCard.
 */
interface QuestionCardProps {
  /** Treść aktualnego pytania do wyświetlenia */
  question: string;
}

/**
 * Karta wyświetlająca aktualne pytanie w wywiadzie.
 * 
 * @param props - Props komponentu
 * @param props.question - Treść pytania
 */
export const QuestionCard: React.FC<QuestionCardProps> = ({ question }) => {
  return (
    <div className="question-card">
      <h3>❓ Aktualne pytanie:</h3>
      <p className="question-text">{question || "Kliknij 'Losuj pytanie' aby rozpocząć"}</p>
    </div>
  );
};
