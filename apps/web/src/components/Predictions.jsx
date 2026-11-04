import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function formatDay(dateStr) {
  if (!dateStr) return "Sem data";
  const [, month, day] = dateStr.split("-");
  return `${day}/${month}`;
}

function pct(p) {
  return `${Math.round(p * 100)}%`;
}

function PredictionCard({ p }) {
  const badge = (team) =>
    team.badge_url && <img src={team.badge_url} alt="" width="24" height="24" loading="lazy" />;

  return (
    <div className="match-card">
      <div className="match-meta">
        <span>{p.match_time}</span>
        {p.venue && <span>{p.venue}</span>}
      </div>

      <div className="match-teams">
        <div className="match-team">
          {badge(p.home_team)}
          <span>{p.home_team.name}</span>
        </div>
        <div className="score-separator">x</div>
        <div className="match-team match-team-away">
          <span>{p.away_team.name}</span>
          {badge(p.away_team)}
        </div>
      </div>

      <div className="pred-bar" title="Probabilidade de vitória do mandante, empate e vitória do visitante">
        <div className="pred-home" style={{ width: pct(p.p_home) }} />
        <div className="pred-draw" style={{ width: pct(p.p_draw) }} />
        <div className="pred-away" style={{ width: pct(p.p_away) }} />
      </div>
      <div className="pred-labels">
        <span>Casa {pct(p.p_home)}</span>
        <span>Empate {pct(p.p_draw)}</span>
        <span>Fora {pct(p.p_away)}</span>
      </div>
    </div>
  );
}

export function Predictions({ serie }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/competitions/${serie}/predictions`)
      .then((r) => {
        if (!r.ok) throw new Error("Não foi possível carregar as previsões.");
        return r.json();
      })
      .then((data) => !cancelled && setItems(data))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [serie]);

  if (loading) return <p className="state-message">Carregando previsões...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (items.length === 0)
    return (
      <p className="state-message">
        Sem previsões para esta série. O modelo cobre as Séries A e B (pontos corridos) e prevê só
        jogos ainda não disputados.
      </p>
    );

  const days = [];
  for (const p of items) {
    const last = days[days.length - 1];
    if (last && last.date === p.match_date) last.items.push(p);
    else days.push({ date: p.match_date, items: [p] });
  }

  const info = items[0];

  return (
    <div>
      {days.map((d) => (
        <section key={d.date ?? "sem-data"} className="phase-section">
          <h3 className="phase-title">{formatDay(d.date)}</h3>
          <div className="matches-list">
            {d.items.map((p) => (
              <PredictionCard key={p.match_id} p={p} />
            ))}
          </div>
        </section>
      ))}
      <p className="metrics-note">
        Probabilidades do modelo {info.model_version}: regressão logística sobre a diferença de Elo,
        treinada com {info.trained_on} jogos finalizados das Séries A e B. Na avaliação em janelas
        crescentes ele reduz o log loss em cerca de 2,6% sobre o chute pela frequência histórica.
        É um ganho real, mas modesto: são probabilidades, não palpites. Atualizado em{" "}
        {new Date(info.generated_at).toLocaleDateString("pt-BR")}.
      </p>
    </div>
  );
}
