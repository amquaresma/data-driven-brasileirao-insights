const TZ = "America/Sao_Paulo";

const formatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: TZ,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

// Data e hora de um jogo no horário de Brasília. O banco guarda em UTC (date_time);
// sem date_time (jogos carregados à mão), devolve os campos como estão.
export function brt(match) {
  if (match?.date_time) {
    const d = new Date(match.date_time);
    if (!Number.isNaN(d.getTime())) {
      const parts = Object.fromEntries(formatter.formatToParts(d).map((p) => [p.type, p.value]));
      return {
        date: `${parts.year}-${parts.month}-${parts.day}`,
        time: `${parts.hour}:${parts.minute}`,
      };
    }
  }
  return { date: match?.match_date ?? null, time: match?.match_time ?? null };
}

export function formatWhen(match) {
  const { date, time } = brt(match);
  if (!date) return "";
  const [y, m, d] = date.split("-");
  return `${d}/${m}/${y}${time ? ` ${time}` : ""}`;
}
