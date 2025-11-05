import React from "react";

interface AdminPanelProps {
  onGenerateResults: () => void;
  onAnalyzeGithub: () => void;
  disabled?: boolean;
}

export const AdminPanel: React.FC<AdminPanelProps> = ({
  onGenerateResults,
  onAnalyzeGithub,
  disabled = false,
}) => {
  return (
    <div className="admin-panel">
      <h3>🛠️ Panel administratora</h3>
      <div className="admin-actions">
        <button className="btn-warning" onClick={onGenerateResults} disabled={disabled}>
          ⚙️ Generacja wyników
        </button>
        <button className="btn-secondary" onClick={onAnalyzeGithub} disabled={disabled}>
          🧪 Analiza GitHuba
        </button>
      </div>
      <p className="admin-hint">Logika tych akcji zostanie dodana później.</p>
    </div>
  );
};
