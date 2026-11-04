import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function Trend({ value }) {
  if (value === null || value === undefined) return <span>-</span>;
  const cls = value > 0 ? "trend-up" : value < 0 ? "trend-down" : "trend-flat";
  const sign = value > 0 ? "+" : "";
  return <span className={cls}>{sign}{value.toFixed(2)}</span>;
}

function num(value, digits = 2) {
  return value === null || value === undefined ? "-" : Number(value).toFixed(digits);
}

export function TeamMetrics({ serie }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${API_URL}/competitions/${serie}/team-metrics`)
      .then((r) => {
        if (!r.ok) throw new Error("Não foi possível carregar as métricas.");
        return r.json();
      })
      .then((data) => !cancelled && setRows(data))
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));

    return () => {
      cancelled = true;
    };
  }, [serie]);

  if (loading) return <p className="state-message">Carregando métricas...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (rows.length === 0)
    return (
      <p className="state-message">
        Ainda não há métricas calculadas para esta série (o Analytics usa jogos finalizados).
      </p>
    );

  return (
    <>
      <table className="standings-table">
        <thead>
          <tr>
            <th>#</th>
            <th style={{ textAlign: "left" }}>Time</th>
            <th title="Rating Elo calculado a partir dos resultados">Elo</th>
            <th title="Tendência: últimos 5 jogos contra os últimos 10">Momentum</th>
            <th title="Forma ponderada (jogo mais recente pesa mais), escala 0 a 3">Forma</th>
            <th title="Sequência atual de vitórias">Seq. V</th>
            <th title="Sequência atual sem perder">Invicto</th>
            <th title="Sequência atual sem sofrer gols">Sem sofrer</th>
            <th title="Instabilidade do desempenho (desvio padrão, últimos 10)">Volat.</th>
            <th title="Média de gols marcados e sofridos nos últimos 5 jogos">GP/GC (5)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.team.id}>
              <td>{i + 1}</td>
              <td className="team-cell">
                {r.team.badge_url && (
                  <img src={r.team.badge_url} alt="" width="20" height="20" loading="lazy" />
                )}
                {r.team.name}
              </td>
              <td>{num(r.elo, 0)}</td>
              <td><Trend value={r.momentum_score} /></td>
              <td>{num(r.weighted_form_score)}</td>
              <td>{r.win_streak ?? "-"}</td>
              <td>{r.unbeaten_streak ?? "-"}</td>
              <td>{r.clean_sheet_streak ?? "-"}</td>
              <td>{num(r.volatility_index)}</td>
              <td>{num(r.goals_for_avg_5, 1)} / {num(r.goals_against_avg_5, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="metrics-note">
        Elo, momentum e volatilidade são índices próprios do projeto, calculados a partir dos
        resultados. Passe o mouse sobre o cabeçalho para ver o que cada um mede.
      </p>
    </>
  );
}
