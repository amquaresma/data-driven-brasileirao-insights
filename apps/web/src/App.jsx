import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function App() {
  const [apiStatus, setApiStatus] = useState("Verificando API...");
  const [error, setError] = useState(null);

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch(`${API_URL}/health`);

        if (!response.ok) {
          throw new Error("A API retornou um erro.");
        }

        const data = await response.json();

        setApiStatus(
          `${data.service} online — versão ${data.version}`,
        );
      } catch (err) {
        setError(err.message);
        setApiStatus("API indisponível");
      }
    }

    checkApi();
  }, []);

  return (
    <main>
      <h1>Data-Driven Brasileirão Insights</h1>

      <p>
        Plataforma de análise de dados, estatística e Machine Learning
        aplicada ao futebol brasileiro.
      </p>

      <section>
        <h2>Status do sistema</h2>

        <p>{apiStatus}</p>

        {error && <p>{error}</p>}
      </section>
    </main>
  );
}

export default App;