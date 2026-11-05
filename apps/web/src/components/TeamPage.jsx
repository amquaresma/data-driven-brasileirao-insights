import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from "chart.js";
import { Line } from "react-chartjs-2";
import { useApi } from "../lib/useApi";
import { brt } from "../lib/datetime";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip);

const API_URL = import.meta.env.VITE_API_URL;

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

function side(match, teamId) {
  const home = match.home_team.id === teamId;
  return {
    home,
    gf: home ? match.home_score : match.away_score,
    ga: home ? match.away_score : match.home_score,
    opp: home ? match.away_team : match.home_team,
  };
}

const letter = (gf, ga) => (gf > ga ? "W" : gf === ga ? "D" : "L");
const pct = (p) => `${Math.round(p * 100)}%`;
const num = (v, d = 2) => (v === null || v === undefined ? "-" : Number(v).toFixed(d));

function shortDate(dateStr) {
  if (!dateStr) return "";
  const [, m, d] = dateStr.split("-");
  return `${d}/${m}`;
}

function Metric({ label, value, hint }) {
  return (
    <div className="metric-card" title={hint}>
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
    </div>
  );
}

export function TeamPage({ serie, teamId, onBack }) {
  const { data, loading, error } = useApi(
    `${API_URL}/competitions/${serie}/teams/${teamId}`,
    "Não foi possível carregar o clube.",
  );

  if (loading) return <p className="state-message">Carregando clube...</p>;
  if (error || !data) return <p className="state-message error">{error ?? "Clube não encontrado."}</p>;

  const { team, standing: st, metrics: m, recent, upcoming, elo_series: elo } = data;
  const text = cssVar("--text-secondary", "#aaa");
  const grid = cssVar("--border", "#333");
  const accent = cssVar("--accent", "#16a34a");

  const chartData = {
    labels: elo.map((p) => shortDate(p.match_date)),
    datasets: [
      {
        label: "Elo antes do jogo",
        data: elo.map((p) => p.elo),
        borderColor: accent,
        backgroundColor: accent,
        pointRadius: 2,
        tension: 0.25,
      },
    ],
  };
  const chartOptions = {
    responsive: true,
    aspectRatio: window.innerWidth < 640 ? 1.3 : 2.6,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: text, maxTicksLimit: 10 }, grid: { color: grid } },
      y: { ticks: { color: text }, grid: { color: grid } },
    },
  };

  return (
    <div className="team-page">
      <button className="back-button" onClick={onBack}>
        ← Voltar
      </button>

      <div className="team-header">
        {team.badge_url && <img src={team.badge_url} alt="" width="56" height="56" />}
        <div>
          <h3 className="team-name">{team.name}</h3>
          {st ? (
            <p className="team-summary">
              {st.position}º · {st.points} pts · {st.matches_played} jogos · {st.wins}V {st.draws}E{" "}
              {st.losses}D · gols {st.goals_for}:{st.goals_against}
              {st.group_name ? ` · ${st.group_name}` : ""}
              {st.legend ? ` · ${st.legend}` : ""}
            </p>
          ) : (
            <p className="team-summary">Sem classificação nesta fase.</p>
          )}
        </div>
      </div>

      {m && (
        <section className="match-detail-section">
          <h3>Métricas (temporada atual)</h3>
          <div className="metric-grid">
            <Metric label="Elo (2026)" value={num(m.elo, 0)} hint="Rating Elo só com os jogos desta temporada" />
            <Metric
              label="Momentum"
              value={m.momentum_score == null ? "-" : `${m.momentum_score > 0 ? "+" : ""}${num(m.momentum_score)}`}
              hint="Últimos 5 jogos contra os últimos 10"
            />
            <Metric label="Forma" value={num(m.weighted_form_score)} hint="Pontos por jogo ponderados, escala 0 a 3" />
            <Metric label="Seq. de vitórias" value={m.win_streak ?? "-"} />
            <Metric label="Invicto" value={m.unbeaten_streak ?? "-"} />
            <Metric label="Sem sofrer gol" value={m.clean_sheet_streak ?? "-"} />
            <Metric label="Volatilidade" value={num(m.volatility_index)} hint="Quanto maior, mais irregular" />
            <Metric
              label="GP / GC (5)"
              value={`${num(m.goals_for_avg_5, 1)} / ${num(m.goals_against_avg_5, 1)}`}
              hint="Média de gols marcados e sofridos nos últimos 5 jogos"
            />
          </div>
        </section>
      )}

      <section className="match-detail-section">
        <h3>Elo ao longo da temporada</h3>
        {elo.length > 1 ? (
          <>
            <div className="chart-card">
              <Line data={chartData} options={chartOptions} />
            </div>
            <p className="metrics-note">
              Elo antes de cada jogo, contínuo desde 2020 (o mesmo usado nas previsões). Por isso difere do
              Elo de 2026 acima, que parte de 1500 no início da temporada.
            </p>
          </>
        ) : (
          <p className="state-message">Sem série de Elo para esta competição.</p>
        )}
      </section>

      <div className="team-lists">
        <section>
          <h3 className="phase-title">Últimos resultados</h3>
          {recent.length === 0 && <p className="state-message">Sem jogos com data.</p>}
          {recent.map((g) => {
            const s = side(g, teamId);
            const l = letter(s.gf, s.ga);
            return (
              <div className="result-row" key={g.id}>
                <span className={`form-badge form-${l}`}>{l}</span>
                <span className="result-opp">
                  {s.home ? "vs" : "em"} {s.opp.name}
                </span>
                <span className="result-score">
                  {s.gf} x {s.ga}
                </span>
                <span className="result-date">{shortDate(brt(g).date)}</span>
              </div>
            );
          })}
        </section>

        <section>
          <h3 className="phase-title">Próximos jogos</h3>
          {upcoming.length === 0 && <p className="state-message">Sem jogos agendados.</p>}
          {upcoming.map((g) => {
            const s = side(g, teamId);
            const w = brt(g);
            const p =
              g.p_home == null ? null : s.home ? [g.p_home, g.p_draw, g.p_away] : [g.p_away, g.p_draw, g.p_home];
            return (
              <div className="result-row upcoming-row" key={g.id}>
                <span className="result-date">
                  {shortDate(w.date)} {w.time}
                </span>
                <span className="result-opp">
                  {s.home ? "vs" : "em"} {s.opp.name}
                </span>
                {p && (
                  <span className="result-prob" title="Probabilidade de vitória, empate e derrota deste time">
                    V {pct(p[0])} · E {pct(p[1])} · D {pct(p[2])}
                  </span>
                )}
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
