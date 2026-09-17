import { useEffect, useState } from "react";
import "./App.css";
import {
  GoalsChart,
  EfficiencyChart,
  GoalDifferenceChart,
  ResultsDistributionChart,
} from "./components/StandingsCharts";
import { MatchesList } from "./components/MatchesList";
import { MatchDetail } from "./components/MatchDetail";

const API_URL = import.meta.env.VITE_API_URL;

const SERIES = [
  { code: "a", label: "Série A" },
  { code: "b", label: "Série B" },
  { code: "c", label: "Série C" },
  { code: "d", label: "Série D" },
];

const VIEWS = [
  { key: "standings", label: "Classificação" },
  { key: "matches", label: "Partidas" },
  { key: "analytics", label: "Análises" },
];

function useStandings(serie) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/competitions/${serie}/standings`)
      .then((r) => {
        if (!r.ok) throw new Error("Não foi possível carregar a classificação.");
        return r.json();
      })
      .then((data) => !cancelled && setEntries(data))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [serie]);

  return { entries, loading, error };
}

function useMatches(serie) {
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/competitions/${serie}/matches`)
      .then((r) => {
        if (!r.ok) throw new Error("Não foi possível carregar as partidas.");
        return r.json();
      })
      .then((data) => !cancelled && setMatches(data))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [serie]);

  return { matches, loading, error };
}

function ApiStatus() {
  const [status, setStatus] = useState("Verificando API...");
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => {
        if (!r.ok) throw new Error("A API retornou um erro.");
        return r.json();
      })
      .then((data) => setStatus(`API online — v${data.version}`))
      .catch((err) => {
        setError(err.message);
        setStatus("API indisponível");
      });
  }, []);

  return (
    <p className="api-status">
      {status}
      {error && <span className="api-error"> — {error}</span>}
    </p>
  );
}

function StandingsView({ serie }) {
  const { entries, loading, error } = useStandings(serie);

  if (loading) return <p className="state-message">Carregando classificação...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (entries.length === 0)
    return (
      <p className="state-message">
        Nenhuma classificação disponível no momento (a competição pode estar
        em fase de mata-mata).
      </p>
    );

  const hasGroups = entries.some((e) => e.group_name);

  return (
    <table className="standings-table">
      <thead>
        <tr>
          <th>#</th>
          {hasGroups && <th>Grupo</th>}
          <th style={{ textAlign: "left" }}>Time</th>
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
                <img src={entry.team.badge_url} alt="" width="20" height="20" loading="lazy" />
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

function AnalyticsView({ serie }) {
  const { entries, loading, error } = useStandings(serie);

  if (loading) return <p className="state-message">Carregando análises...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (entries.length === 0)
    return <p className="state-message">Sem dados suficientes para análise no momento.</p>;

  return (
    <div className="charts-grid">
      <GoalsChart entries={entries} />
      <EfficiencyChart entries={entries} />
      <GoalDifferenceChart entries={entries} />
      <ResultsDistributionChart entries={entries} />
    </div>
  );
}

function MatchesView({ serie }) {
  const { matches, loading, error } = useMatches(serie);
  const [selectedMatchId, setSelectedMatchId] = useState(null);

  if (selectedMatchId) {
    return <MatchDetail matchId={selectedMatchId} onBack={() => setSelectedMatchId(null)} />;
  }

  if (loading) return <p className="state-message">Carregando partidas...</p>;
  if (error) return <p className="state-message error">{error}</p>;

  return <MatchesList matches={matches} onSelectMatch={setSelectedMatchId} />;
}

function App() {
  const [serie, setSerie] = useState("a");
  const [view, setView] = useState("standings");

  const currentSerieLabel = SERIES.find((s) => s.code === serie)?.label;
  const currentViewLabel = VIEWS.find((v) => v.key === view)?.label;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>Brasileirão Insights</h1>
          <span>Data-driven football analytics</span>
        </div>

        <div>
          <div className="sidebar-section-label">Competições</div>
          <nav className="sidebar-nav">
            {SERIES.map((s) => (
              <button
                key={s.code}
                className={`sidebar-nav-item ${s.code === serie ? "active" : ""}`}
                onClick={() => setSerie(s.code)}
              >
                {s.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-footer">
          <ApiStatus />
        </div>
      </aside>

      <main className="main-content">
        <div className="page-header">
          <h2>
            {currentSerieLabel} · {currentViewLabel}
          </h2>
        </div>

        <nav className="view-tabs">
          {VIEWS.map((v) => (
            <button
              key={v.key}
              className={v.key === view ? "active" : ""}
              onClick={() => setView(v.key)}
            >
              {v.label}
            </button>
          ))}
        </nav>

        {view === "standings" && <StandingsView serie={serie} />}
        {view === "matches" && <MatchesView serie={serie} />}
        {view === "analytics" && <AnalyticsView serie={serie} />}
      </main>
    </div>
  );
}

export default App;
