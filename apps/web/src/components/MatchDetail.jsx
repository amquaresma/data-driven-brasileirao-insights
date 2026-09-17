import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

// Estatísticas priorizadas para a visão compacta (nomes exatos como
// vêm da Highlightly). O restante fica disponível na lista completa.
const KEY_STATS = [
  "Expected Goals",
  "Possession",
  "Shots on target",
  "Total passes",
  "Corners",
  "Fouls",
  "Yellow cards",
  "Red cards",
];

function formatStatValue(name, value) {
  if (name === "Possession") return `${Math.round(value * 100)}%`;
  if (name === "Expected Goals") return value.toFixed(2);
  return value;
}

function StatRow({ label, homeValue, awayValue }) {
  const home = homeValue ?? 0;
  const away = awayValue ?? 0;
  const total = home + away || 1;
  const homePct = (home / total) * 100;

  return (
    <div className="stat-row">
      <div className="stat-row-values">
        <span>{homeValue ?? "-"}</span>
        <span className="stat-row-label">{label}</span>
        <span>{awayValue ?? "-"}</span>
      </div>
      <div className="stat-row-bar">
        <div className="stat-row-bar-home" style={{ width: `${homePct}%` }} />
        <div className="stat-row-bar-away" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  );
}

function EventIcon({ type }) {
  const icons = {
    Goal: "⚽",
    "Yellow Card": "🟨",
    "Red Card": "🟥",
    Substitution: "🔄",
  };
  return <span className="event-icon">{icons[type] || "•"}</span>;
}

export function MatchDetail({ matchId, onBack }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAllStats, setShowAllStats] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchDetail() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_URL}/competitions/matches/${matchId}/detail`);
        if (!response.ok) throw new Error("Não foi possível carregar o detalhe da partida.");
        const data = await response.json();
        if (!cancelled) setDetail(data);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchDetail();
    return () => {
      cancelled = true;
    };
  }, [matchId]);

  if (loading) return <p className="state-message">Carregando detalhe...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (!detail) return null;

  const [homeStats, awayStats] = detail.statistics;
  const hasStats = homeStats && awayStats;

  const statMap = (teamStats) =>
    Object.fromEntries((teamStats?.statistics ?? []).map((s) => [s.stat_name, s.stat_value]));

  const homeStatMap = hasStats ? statMap(homeStats) : {};
  const awayStatMap = hasStats ? statMap(awayStats) : {};

  const allStatNames = hasStats
    ? [...new Set([...Object.keys(homeStatMap), ...Object.keys(awayStatMap)])]
    : [];
  const otherStatNames = allStatNames.filter((n) => !KEY_STATS.includes(n));

  return (
    <div className="match-detail">
      <button className="back-button" onClick={onBack}>
        ← Voltar
      </button>

      <div className="match-detail-header">
        <div className="match-detail-team">
          {detail.home_team.badge_url && <img src={detail.home_team.badge_url} alt="" width="40" height="40" />}
          <span>{detail.home_team.name}</span>
        </div>
        <div className="match-detail-score">
          <span>{detail.home_score ?? "-"}</span>
          <span>x</span>
          <span>{detail.away_score ?? "-"}</span>
        </div>
        <div className="match-detail-team match-detail-team-away">
          <span>{detail.away_team.name}</span>
          {detail.away_team.badge_url && <img src={detail.away_team.badge_url} alt="" width="40" height="40" />}
        </div>
      </div>
      <p className="match-detail-meta">
        {detail.match_date} {detail.match_time} {detail.venue && `· ${detail.venue}`}
      </p>

      {hasStats ? (
        <>
          <section className="match-detail-section">
            <h3>Estatísticas</h3>
            {KEY_STATS.filter((name) => name in homeStatMap || name in awayStatMap).map((name) => (
              <StatRow
                key={name}
                label={name}
                homeValue={homeStatMap[name] !== undefined ? formatStatValue(name, homeStatMap[name]) : null}
                awayValue={awayStatMap[name] !== undefined ? formatStatValue(name, awayStatMap[name]) : null}
              />
            ))}

            {otherStatNames.length > 0 && (
              <>
                <button className="toggle-stats-button" onClick={() => setShowAllStats((v) => !v)}>
                  {showAllStats ? "Ocultar" : "Ver"} todas as estatísticas ({otherStatNames.length})
                </button>
                {showAllStats &&
                  otherStatNames.map((name) => (
                    <StatRow
                      key={name}
                      label={name}
                      homeValue={homeStatMap[name] ?? null}
                      awayValue={awayStatMap[name] ?? null}
                    />
                  ))}
              </>
            )}
          </section>
        </>
      ) : (
        <p className="state-message">Estatísticas ainda não disponíveis para esta partida.</p>
      )}

      {detail.events.length > 0 && (
        <section className="match-detail-section">
          <h3>Linha do tempo</h3>
          <div className="events-timeline">
            {detail.events.map((event, i) => (
              <div key={i} className="event-row">
                <span className="event-minute">{event.minute}'</span>
                <EventIcon type={event.event_type} />
                <span className="event-player">
                  {event.player_name}
                  {event.substituted_player_name && ` ⟶ ${event.substituted_player_name}`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
