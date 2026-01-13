import { useState } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";

function App() {
  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition();

  const [initializing, setInitializing] = useState(false); // stan ładowania mikrofonu

  if (!browserSupportsSpeechRecognition) {
    return <span>Twoja przeglądarka nie wspiera rozpoznawania mowy.</span>;
  }

  const startListening = () => {
    // jeśli już słucha albo właśnie się uruchamia – ignoruj
    if (listening || initializing) return;

    console.log("START");
    setInitializing(true);

    try {
      SpeechRecognition.startListening({
        continuous: true,
        language: "pl-PL",
      });
    } catch (e) {
      console.error("Błąd przy startListening:", e);
      setInitializing(false);
      return;
    }

    // „sztuczne” okienko ładowania ~1,5 sekundy
    setTimeout(() => {
      setInitializing(false);
    }, 1500);
  };

  const stopListening = () => {
    if (!listening && !initializing) return;

    console.log("STOP");
    setInitializing(false);
    SpeechRecognition.stopListening();

    // 🔥 auto-zapis do pliku TXT po kliknięciu STOP
    if (!transcript || transcript.trim() === "") {
      console.log("Brak tekstu do zapisania.");
      return;
    }

    const blob = new Blob([transcript], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = "mowa.txt";
    a.click();

    URL.revokeObjectURL(url);
  };

  return (
    <>
      {/* Prosty CSS dla animacji (spinner) */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .spinner {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border: 3px solid #ddd;
          border-top-color: #333;
          animation: spin 0.8s linear infinite;
          margin-right: 8px;
        }

        .loading-bar {
          display: flex;
          align-items: center;
          background: #f5f5f5;
          padding: 0.5rem 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
          font-size: 0.95rem;
        }
      `}</style>

      <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
        <h1>Rozpoznawanie mowy </h1>

        {/* Pasek ładowania mikrofonu */}
        {initializing && (
          <div className="loading-bar">
            <div className="spinner" />
            <span>Uruchamianie mikrofonu…</span>
          </div>
        )}

        <p>Status: {listening ? "słucham..." : " nie słucham"}</p>
        <p>Wsparcie przeglądarki: {browserSupportsSpeechRecognition ? "TAK" : "NIE"}</p>

        <button
          onClick={startListening}
          style={{ marginRight: "0.5rem" }}
          disabled={initializing}
        >
          Start (PL)
        </button>

        <button
          onClick={stopListening}
          style={{ marginRight: "0.5rem" }}
          disabled={initializing}
        >
          Stop
        </button>

        <button onClick={resetTranscript}>Wyczyść tekst</button>

        <h2>Tekst z mikrofonu:</h2>
        <textarea
          value={transcript}
          readOnly
          rows={8}
          cols={60}
          style={{ marginTop: "1rem", padding: "0.5rem" }}
        />
      </div>
    </>
  );
}

export default App;
