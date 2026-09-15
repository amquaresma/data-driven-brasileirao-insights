import { useEffect, useState } from "react";
import "./App.css";
import {
  GoalsChart,
  EfficiencyChart,
  GoalDifferenceChart,
  ResultsDistributionChart,
} from "./components/StandingsCharts";

const API_URL = import.meta.env.VITE_API_URL;

const SERIES = [
  { code: "a", label: "Série A" },
  { code: "b", label: "Série B" },
  { code: "c", label: "Série C" },
  { code: "d", label: "Série D" },
];

function ApiStatus() {
  const [status, setStatus] = useState("Verificando API...");
  const [error, setError] = useState(null);

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch(`${API_URL}/health`);
        if (!response.ok) throw new Error("A API retornou um erro.");
        const data = await response.json();
        setStatus(`${data.service} online — versão ${data.version}`);
      } catch (err) {
        setError(err.message);
        setStatus("API indisponível");
      }
    }
    checkApi();
  }, []);

  return (
    <p className="api-status">
      {status}
      {error && <span className="api-error"> — {error}</span>}
    </p>
  );
}

function StandingsTable({ entries }) {
  if (entries.length === 0) return null;

  const hasGroups = entries.some((e) => e.group_name);

  return (
    <table className="standings-table">
      <thead>
        <tr>
          <th>#</th>
          {hasGroups && <th>Grupo</th>}
          <th>Time</th>
          <th>P</th>
          <th>J</th>
          <th>V</th>
          <th>E</th>
          <th>D</th>
          <th>GP</th>
          <th>GC</th>
          <th>SG</th>
          <th>Forma</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry, i) => (
          <tr key={`${entry.team.id}-${entry.group_name ?? i}`}>
            <td>{entry.position}</td>
            {hasGroups && <td>{entry.group_name}</td>}
            <td className="team-cell">
              {entry.team.badge_url && (
                <img
                  src={entry.team.badge_url}
                  alt=""
                  width="20"
                  height="20"
                  loading="lazy"
                />
              )}
              {entry.team.name}
            </td>
            <td>{entry.points}</td>
            <td>{entry.matches_played}</td>
            <td>{entry.wins}</td>
            <td>{entry.draws}</td>
            <td>{entry.losses}</td>
            <td>{entry.goals_for}</td>
            <td>{entry.goals_against}</td>
            <td>{entry.goal_difference}</td>
            <td className="form-cell">
              {(entry.recent_form ?? []).map((result, idx) => (
                <span key={idx} className={`form-badge form-${result}`}>
                  {result}
                </span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SeriesView({ serie }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchStandings() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${API_URL}/competitions/${serie}/standings`,
        );
        if (!response.ok) throw new Error("Não foi possível carregar a classificação.");
        const data = await response.json();
        if (!cancelled) setEntries(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchStandings();
    return () => {
      cancelled = true;
    };
  }, [serie]);

  if (loading) return <p className="state-message">Carregando classificação...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (entries.length === 0)
    return (
      <p className="state-message">
        Nenhuma classificação disponível no momento (a competição pode estar
        em fase de mata-mata).
      </p>
    );

  return (
    <>
      <StandingsTable entries={entries} />

      <section className="charts-section">
        <h2>Análises</h2>
        <div className="charts-grid">
          <GoalsChart entries={entries} />
          <EfficiencyChart entries={entries} />
          <GoalDifferenceChart entries={entries} />
          <ResultsDistributionChart entries={entries} />
        </div>
      </section>
    </>
  );
}

function App() {
  const [serie, setSerie] = useState("a");

  return (
    <main>
      <header>
        <h1>Data-Driven Brasileirão Insights</h1>
        <p>
          Plataforma de análise de dados, estatística e Machine Learning
          aplicada ao futebol brasileiro.
        </p>
        <ApiStatus />
      </header>

      <nav className="series-tabs">
        {SERIES.map((s) => (
          <button
            key={s.code}
            className={s.code === serie ? "active" : ""}
            onClick={() => setSerie(s.code)}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <SeriesView serie={serie} />
    </main>
  );
}

export default App;
