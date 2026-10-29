function formatDate(dateStr) {
  if (!dateStr) return "";
  const [, month, day] = dateStr.split("-");
  return `${day}/${month}`;
}

function statusLabel(status) {
  const labels = {
    finished: "Encerrado",
    scheduled: "Agendado",
    live: "Ao vivo",
    Finished: "Encerrado",
    "Not started": "Agendado",
  };
  return labels[status] || status || "";
}

function legLabel(leg) {
  return leg === 1 ? "Ida" : leg === 2 ? "Volta" : "";
}

function Score({ match }) {
  const hasPens = match.penalties_home != null && match.penalties_away != null;
  return (
    <div className="match-score">
      {hasPens && <span className="score-pens">({match.penalties_home})</span>}
      <span>{match.home_score ?? "-"}</span>
      <span className="score-separator">x</span>
      <span>{match.away_score ?? "-"}</span>
      {hasPens && <span className="score-pens">({match.penalties_away})</span>}
    </div>
  );
}

function MatchCard({ match, onSelectMatch }) {
  return (
    <button
      className={`match-card status-${match.status} match-card-clickable`}
      onClick={() => onSelectMatch(match.id)}
    >
      <div className="match-meta">
        {match.leg && <span>{legLabel(match.leg)}</span>}
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

        <Score match={match} />

        <div className="match-team match-team-away">
          <span>{match.away_team.name}</span>
          {match.away_team.badge_url && (
            <img src={match.away_team.badge_url} alt="" width="24" height="24" />
          )}
        </div>
      </div>

      {match.venue && <div className="match-venue">{match.venue}</div>}
    </button>
  );
}

function TieTeam({ team, winner, away }) {
  const badge = team.badge_url && <img src={team.badge_url} alt="" width="24" height="24" />;
  return (
    <div className={`tie-team ${away ? "away" : ""} ${winner ? "winner" : ""}`}>
      {!away && badge}
      <span>{team.name}</span>
      {away && badge}
    </div>
  );
}

// Confronto de mata-mata: ida e volta num card só, com agregado e classificado.
function TieCard({ games }) {
  const [g1, g2] = [...games].sort((a, b) => (a.leg ?? 0) - (b.leg ?? 0));
  const a = g1.home_team;
  const b = g1.away_team;
  const played = g1.home_score != null && g2.home_score != null;
  const aGoals = (g1.home_score ?? 0) + (g2.away_score ?? 0);
  const bGoals = (g1.away_score ?? 0) + (g2.home_score ?? 0);

  const pens = games.find((g) => g.penalties_home != null && g.penalties_away != null);
  const penA = pens ? (pens.home_team.id === a.id ? pens.penalties_home : pens.penalties_away) : null;
  const penB = pens ? (pens.home_team.id === a.id ? pens.penalties_away : pens.penalties_home) : null;

  let winner = null;
  if (played) {
    if (aGoals !== bGoals) winner = aGoals > bGoals ? a : b;
    else if (pens && penA !== penB) winner = penA > penB ? a : b;
  }

  return (
    <div className="match-card tie-card">
      <div className="tie-main">
        <TieTeam team={a} winner={winner?.id === a.id} />
        <div className="tie-agg">
          {pens && <span className="score-pens">({penA})</span>}
          <span>{played ? aGoals : "-"}</span>
          <span className="score-separator">x</span>
          <span>{played ? bGoals : "-"}</span>
          {pens && <span className="score-pens">({penB})</span>}
        </div>
        <TieTeam team={b} winner={winner?.id === b.id} away />
      </div>
      <div className="tie-legs">
        {[g1, g2].map((g) => (
          <div key={g.id}>
            {legLabel(g.leg)}: {g.home_team.name} {g.home_score ?? "-"} x {g.away_score ?? "-"}{" "}
            {g.away_team.name}
          </div>
        ))}
      </div>
    </div>
  );
}

function groupTies(items) {
  const out = [];
  for (const m of items) {
    const last = out[out.length - 1];
    if (m.tie_key && last && last.tieKey === m.tie_key) last.games.push(m);
    else out.push({ tieKey: m.tie_key, games: [m] });
  }
  return out;
}

function PhaseBlock({ items, onSelectMatch }) {
  return (
    <div className="matches-list">
      {groupTies(items).map((t) =>
        t.games.length === 2 ? (
          <TieCard key={t.games[0].id} games={t.games} />
        ) : (
          t.games.map((m) => <MatchCard key={m.id} match={m} onSelectMatch={onSelectMatch} />)
        ),
      )}
    </div>
  );
}

export function MatchesList({ matches, onSelectMatch }) {
  if (matches.length === 0) {
    return <p className="state-message">Nenhuma partida disponível no momento.</p>;
  }

  if (!matches.some((m) => m.phase_name)) {
    return (
      <div className="matches-list">
        {matches.map((m) => (
          <MatchCard key={m.id} match={m} onSelectMatch={onSelectMatch} />
        ))}
      </div>
    );
  }

  const sections = [];
  for (const m of matches) {
    const name = m.phase_name || "Outros jogos";
    const last = sections[sections.length - 1];
    if (last && last.name === name) last.items.push(m);
    else sections.push({ name, items: [m] });
  }

  return (
    <div>
      {sections.map((s) => (
        <section key={s.name} className="phase-section">
          <h3 className="phase-title">{s.name}</h3>
          <PhaseBlock items={s.items} onSelectMatch={onSelectMatch} />
        </section>
      ))}
    </div>
  );
}
