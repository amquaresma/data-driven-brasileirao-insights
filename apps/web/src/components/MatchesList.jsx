function formatDate(dateStr) {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-");
  return `${day}/${month}`;
}

function statusLabel(status) {
  const labels = {
    finished: "Encerrado",
    scheduled: "Agendado",
    live: "Ao vivo",
  };
  return labels[status] || status || "";
}

export function MatchesList({ matches }) {
  if (matches.length === 0) {
    return <p className="state-message">Nenhuma partida disponível no momento.</p>;
  }

  return (
    <div className="matches-list">
      {matches.map((match) => (
        <div key={match.id} className={`match-card status-${match.status}`}>
          <div className="match-meta">
            <span>{formatDate(match.match_date)}</span>
            <span>{match.match_time}</span>
            <span className="match-status">{statusLabel(match.status)}</span>
          </div>

          <div className="match-teams">
            <div className="match-team">
              {match.home_team.badge_url && (
                <img src={match.home_team.badge_url} alt="" width="24" height="24" />
              )}
              <span>{match.home_team.name}</span>
            </div>

            <div className="match-score">
              <span>{match.home_score ?? "-"}</span>
              <span className="score-separator">x</span>
              <span>{match.away_score ?? "-"}</span>
            </div>

            <div className="match-team match-team-away">
              <span>{match.away_team.name}</span>
              {match.away_team.badge_url && (
                <img src={match.away_team.badge_url} alt="" width="24" height="24" />
              )}
            </div>
          </div>

          {match.venue && <div className="match-venue">{match.venue}</div>}
        </div>
      ))}
    </div>
  );
}
