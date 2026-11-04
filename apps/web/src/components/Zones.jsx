import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL;

function norm(text) {
  return (text || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

// Cor por nome da legenda que a fonte envia (a posição nunca é fixa no código).
export function zoneColor(legend) {
  if (!legend) return null;
  const n = norm(legend);
  if (n.includes("libertadores") && n.includes("pre")) return "#06b6d4";
  if (n.includes("libertadores")) return "#3b82f6";
  if (n.includes("sul") && n.includes("americana")) return "#eab308";
  if (n.includes("rebaix") || n.includes("serie c")) return "#ef4444";
  if (n.includes("acesso") || n.includes("serie a")) return "#22c55e";
  return "#a78bfa";
}

export function zoneStyle(legend) {
  const color = zoneColor(legend);
  return color ? { boxShadow: `inset 4px 0 0 ${color}` } : undefined;
}

function formatPositions(positions) {
  const ranges = [];
  for (const p of positions) {
    const last = ranges[ranges.length - 1];
    if (last && p === last[1] + 1) last[1] = p;
    else ranges.push([p, p]);
  }
  return ranges.map(([a, b]) => (a === b ? `${a}º` : `${a}º a ${b}º`)).join(", ");
}

export function ZonesAside({ serie }) {
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setEntries(null);
    fetch(`${API_URL}/competitions/${serie}/standings`)
      .then((r) => (r.ok ? r.json() : []))
      .then((d) => !cancelled && setEntries(d))
      .catch(() => !cancelled && setEntries([]));
    return () => {
      cancelled = true;
    };
  }, [serie]);

  const byLegend = new Map();
  for (const e of entries ?? []) {
    if (!e.legend) continue;
    byLegend.set(e.legend, [...(byLegend.get(e.legend) ?? []), e.position]);
  }
  const zones = [...byLegend.entries()]
    .map(([name, positions]) => ({ name, positions: positions.sort((a, b) => a - b) }))
    .sort((a, b) => a.positions[0] - b.positions[0]);

  return (
    <>
      <h3>Legenda da tabela</h3>
      {entries === null && <p>Carregando...</p>}
      {entries !== null && zones.length === 0 && <p>A fonte não informa zonas para esta série agora.</p>}
      <div className="legend-list">
        {zones.map((z) => (
          <div className="legend-item" key={z.name}>
            <span className="legend-visual">
              <span className="legend-swatch" style={{ background: zoneColor(z.name) }} />
            </span>
            <span>
              <b>{z.name}</b>
              <br />
              {formatPositions(z.positions)}
            </span>
          </div>
        ))}
      </div>

      <h4>Como ler</h4>
      <p>
        A faixa colorida à esquerda de cada linha marca a zona do time. Times sem faixa estão fora de
        qualquer zona.
      </p>
      <p>
        As colunas: <b>P</b> pontos, <b>J</b> jogos, <b>V</b> vitórias, <b>E</b> empates, <b>D</b>{" "}
        derrotas, <b>GP</b> gols pró, <b>GC</b> gols contra, <b>SG</b> saldo de gols. Em <b>Forma</b>,
        cada quadrado é um dos últimos jogos (verde V, cinza E, vermelho D), com o mais recente à
        direita.
      </p>

      <h4>Por que as zonas podem mudar</h4>
      <p>
        Elas vêm da fonte e não são fixas. Algumas vagas dependem de outras competições: segundo o
        regulamento da própria fonte, se o campeão da Libertadores, o campeão da Sul-Americana ou um
        finalista da Copa do Brasil estiver entre os primeiros, a vaga passa ao time seguinte, e a
        faixa muda de posição. A tabela acompanha quando a classificação é atualizada.
      </p>
    </>
  );
}
