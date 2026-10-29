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

function useCompetition(serie) {
  const [competition, setCompetition] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/competitions`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => !cancelled && setCompetition(list.find((c) => c.code === serie) ?? null))
      .catch(() => !cancelled && setCompetition(null));
    return () => {
      cancelled = true;
    };
  }, [serie]);

  return competition;
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

function StandingsTable({ rows }) {
  return (
    <table className="standings-table">
      <thead>
        <tr>
          <th>#</th>
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
        {rows.map((entry) => (
          <tr key={entry.team.id}>
            <td>{entry.position}</td>
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

function StandingsView({ serie, phase }) {
  const { entries, loading, error } = useStandings(serie);

  if (loading) return <p className="state-message">Carregando classificação...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (entries.length === 0)
    return (
      <p className="state-message">
        {phase ? `Fase atual: ${phase}. ` : ""}
        Esta fase não tem classificação por pontos. Veja os jogos na aba Partidas.
      </p>
    );

  // fase -> grupo -> linhas (a API já devolve ordenado)
  const phases = [];
  for (const e of entries) {
    const pName = e.phase_name ?? null;
    let p = phases.find((x) => x.name === pName);
    if (!p) {
      p = { name: pName, groups: [] };
      phases.push(p);
    }
    const gName = e.group_name ?? null;
    let g = p.groups.find((x) => x.name === gName);
    if (!g) {
      g = { name: gName, rows: [] };
      p.groups.push(g);
    }
    g.rows.push(e);
  }

  return (
    <div>
      {phases.map((p) => (
        <section key={p.name ?? "unica"} className="phase-section">
          {p.name && <h3 className="phase-title">{p.name}</h3>}
          {p.groups.map((g) => (
            <div key={g.name ?? "tabela"} className="group-block">
              {p.groups.length > 1 && g.name && <h4 className="group-title">{g.name}</h4>}
              <StandingsTable rows={g.rows} />
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}

function pickChartEntries(entries) {
  const byPhase = new Map();
  for (const e of entries) {
    const key = e.phase_name ?? "";
    byPhase.set(key, [...(byPhase.get(key) ?? []), e]);
  }
  const fits = [...byPhase.entries()]
    .filter(([, list]) => list.length <= 24)
    .sort((a, b) => b[1].length - a[1].length);
  return fits.length ? { phase: fits[0][0], list: fits[0][1] } : null;
}

function AnalyticsView({ serie }) {
  const { entries, loading, error } = useStandings(serie);

  if (loading) return <p className="state-message">Carregando análises...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (entries.length === 0)
    return <p className="state-message">Sem dados suficientes para análise no momento.</p>;

  const picked = pickChartEntries(entries);
  if (!picked)
    return (
      <p className="state-message">
        Os gráficos comparam até 24 times por vez. Esta série tem {entries.length} times em vários grupos.
      </p>
    );

  return (
    <>
      {picked.phase && <p className="metrics-note">Base dos gráficos: {picked.phase}</p>}
      <div className="charts-grid">
        <GoalsChart entries={picked.list} />
        <EfficiencyChart entries={picked.list} />
        <GoalDifferenceChart entries={picked.list} />
        <ResultsDistributionChart entries={picked.list} />
      </div>
    </>
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
  const competition = useCompetition(serie);

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
          {competition?.phase_description && (
            <span className="api-status">Fase: {competition.phase_description}</span>
          )}
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

        {view === "standings" && <StandingsView serie={serie} phase={competition?.phase_description} />}
        {view === "matches" && <MatchesView serie={serie} />}
        {view === "analytics" && <AnalyticsView serie={serie} />}
      </main>
    </div>
  );
}

export default App;
