import { useState } from "react";
import { useApi } from "../lib/useApi";
import { TeamPage } from "./TeamPage";

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

const COLUMNS = [
  { key: "team", label: "Time", title: "Ordem alfabética", text: true, get: (r) => r.team.name },
  { key: "elo", label: "Elo", title: "Rating Elo calculado a partir dos resultados", get: (r) => r.elo },
  { key: "momentum", label: "Momentum", title: "Tendência: últimos 5 jogos contra os últimos 10", get: (r) => r.momentum_score },
  { key: "form", label: "Forma", title: "Forma ponderada (jogo mais recente pesa mais), escala 0 a 3", get: (r) => r.weighted_form_score },
  { key: "win", label: "Seq. V", title: "Sequência atual de vitórias", get: (r) => r.win_streak },
  { key: "unbeaten", label: "Invicto", title: "Sequência atual sem perder", get: (r) => r.unbeaten_streak },
  { key: "clean", label: "Sem sofrer", title: "Sequência atual sem sofrer gols", get: (r) => r.clean_sheet_streak },
  { key: "vol", label: "Volat.", title: "Instabilidade do desempenho (desvio padrão, últimos 10)", get: (r) => r.volatility_index },
  { key: "gf", label: "GP/GC (5)", title: "Média de gols marcados e sofridos nos últimos 5 jogos (ordena pelos gols marcados)", get: (r) => r.goals_for_avg_5 },
];

function sortRows(rows, column, dir) {
  const sign = dir === "asc" ? 1 : -1;
  return [...rows].sort((a, b) => {
    const va = column.get(a);
    const vb = column.get(b);
    const aEmpty = va === null || va === undefined;
    const bEmpty = vb === null || vb === undefined;
    if (aEmpty && bEmpty) return 0;
    if (aEmpty) return 1; // vazios sempre no fim
    if (bEmpty) return -1;
    const cmp = column.text ? String(va).localeCompare(String(vb), "pt-BR") : Number(va) - Number(vb);
    return cmp * sign;
  });
}

function SortHeader({ column, sort, onSort }) {
  const active = sort.key === column.key;
  return (
    <th
      className="sortable"
      style={column.text ? { textAlign: "left" } : undefined}
      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
    >
      <button type="button" className="sort-button" title={column.title} onClick={() => onSort(column)}>
        {column.label}
        <span className={`sort-arrow ${active ? "active" : ""}`}>
          {active ? (sort.dir === "asc" ? "▲" : "▼") : "↕"}
        </span>
      </button>
    </th>
  );
}

export function TeamMetrics({ serie }) {
  const { data, loading, error } = useApi(
    `${API_URL}/competitions/${serie}/team-metrics`,
    "Não foi possível carregar as métricas.",
  );
  const rows = data ?? [];
  const [sort, setSort] = useState({ key: "elo", dir: "desc" });
  const [teamId, setTeamId] = useState(null);

  if (teamId) return <TeamPage serie={serie} teamId={teamId} onBack={() => setTeamId(null)} />;


  if (loading) return <p className="state-message">Carregando métricas...</p>;
  if (error) return <p className="state-message error">{error}</p>;
  if (rows.length === 0)
    return (
      <p className="state-message">
        Ainda não há métricas calculadas para esta série (o Analytics usa jogos finalizados).
      </p>
    );

  // A posição pelo Elo é fixa: não muda quando a tabela é reordenada.
  const eloRank = new Map(sortRows(rows, COLUMNS[1], "desc").map((r, i) => [r.team.id, i + 1]));

  const column = COLUMNS.find((c) => c.key === sort.key);
  const sorted = sortRows(rows, column, sort.dir);

  function onSort(col) {
    setSort((prev) =>
      prev.key === col.key
        ? { key: col.key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key: col.key, dir: col.text ? "asc" : "desc" },
    );
  }

  return (
    <>
      <div className="table-scroll">
        <table className="standings-table">
        <thead>
          <tr>
            <th title="Posição pelo Elo (fixa ao reordenar)">#</th>
            {COLUMNS.map((c) => (
              <SortHeader key={c.key} column={c} sort={sort} onSort={onSort} />
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={r.team.id}>
              <td>{eloRank.get(r.team.id)}</td>
              <td className="team-cell">
                {r.team.badge_url && (
                  <img src={r.team.badge_url} alt="" width="20" height="20" loading="lazy" />
                )}
                <button type="button" className="link-button" onClick={() => setTeamId(r.team.id)}>
                  {r.team.name}
                </button>
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
    </div>
      <p className="metrics-note">
        Elo, momentum e volatilidade são índices próprios do projeto, calculados a partir dos
        resultados. Clique no cabeçalho de uma coluna para ordenar, e de novo para inverter.
      </p>
    </>
  );
}
