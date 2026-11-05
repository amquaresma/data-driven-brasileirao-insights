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
