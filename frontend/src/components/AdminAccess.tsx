// src/components/AdminAccess.tsx
import React, { useState } from "react";

const ADMIN_KEY = "admin123"; // Klucz dostępu do panelu admina

interface AdminAccessProps {
    onAccessGranted: () => void;
}

export const AdminAccess: React.FC<AdminAccessProps> = ({ onAccessGranted }) => {
    const [inputKey, setInputKey] = useState("");
    const [error, setError] = useState("");
    const [showInput, setShowInput] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputKey === ADMIN_KEY) {
            setError("");
            onAccessGranted();
        } else {
            setError("Nieprawidłowy klucz dostępu");
            setInputKey("");
        }
    };

    if (!showInput) {
        return (
            <div className="admin-access">
                <button
                    className="btn-admin-access"
                    onClick={() => setShowInput(true)}
                >
                    🔐 Panel Administratora
                </button>
            </div>
        );
    }

    return (
        <div className="admin-access">
            <div className="admin-access-modal">
                <h3>🔒 Dostęp do Panelu Administratora</h3>
                <form onSubmit={handleSubmit}>
                    <input
                        type="password"
                        value={inputKey}
                        onChange={(e) => setInputKey(e.target.value)}
                        placeholder="Wprowadź klucz dostępu..."
                        className="admin-key-input"
                        autoFocus
                    />
                    <div className="admin-access-buttons">
                        <button type="submit" className="btn-primary">
                            Potwierdź
                        </button>
                        <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => {
                                setShowInput(false);
                                setError("");
                                setInputKey("");
                            }}
                        >
                            Anuluj
                        </button>
                    </div>
                </form>
                {error && <div className="admin-access-error">❌ {error}</div>}
            </div>
        </div>
    );
};
