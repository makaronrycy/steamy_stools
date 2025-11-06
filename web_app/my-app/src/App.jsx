import { useState } from 'react';

function App() {
  const [count, setCount] = useState(0);

  return (
    <main
      style={{
        fontFamily: 'system-ui, Arial, sans-serif',
        padding: '2rem',
        maxWidth: 720,
        margin: '0 auto',
        lineHeight: 1.5
      }}
    >
      <h1>Witaj w React + Vite</h1>
      <p>To prosty licznik z hookiem useState.</p>
      <button
        onClick={() => setCount((c) => c + 1)}
        style={{
          padding: '0.6rem 1rem',
          fontSize: '1rem',
          cursor: 'pointer'
        }}
      >
        Kliknięto: {count}
      </button>
    </main>
  );
}

export default App;
