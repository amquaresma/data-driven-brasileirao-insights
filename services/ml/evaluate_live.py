"""
Calibração das previsões em produção: compara a previsão salva em match_predictions
com o resultado real dos jogos já disputados. Usa, para cada jogo, a previsão mais
recente gerada ANTES do início da partida.

Uso:
    python evaluate_live.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

from infrastructure.supabase import get_supabase_client

PAGE = 1000
MIN_GAMES = 100  # abaixo disso o resultado é só ilustrativo


def fetch(client, table, select, **filters):
    rows, offset = [], 0
    while True:
        q = client.table(table).select(select)
        for k, v in filters.items():
            q = q.eq(k, v)
        page = q.range(offset, offset + PAGE - 1).execute().data
        rows += page
        if len(page) < PAGE:
            return rows
        offset += PAGE


def main() -> None:
    client = get_supabase_client()
    preds = fetch(client, "match_predictions", "match_id, model_version, p_home, p_draw, p_away, p_over_2_5, generated_at")
    if not preds:
        print("Ainda não há previsões salvas.")
        return

    ids = sorted({p["match_id"] for p in preds})
    matches = {}
    for i in range(0, len(ids), 200):
        for m in client.table("matches").select("id, date_time, status, home_score, away_score").in_("id", ids[i:i + 200]).execute().data:
            matches[m["id"]] = m

    rows = []
    for p in preds:
        m = matches.get(p["match_id"])
        if not m or "Finish" not in (m["status"] or "") or m["home_score"] is None or not m["date_time"]:
            continue
        kickoff = datetime.fromisoformat(m["date_time"].replace("Z", "+00:00"))
        made = datetime.fromisoformat(p["generated_at"].replace("Z", "+00:00"))
        if made >= kickoff:  # só vale previsão feita antes do jogo
            continue
        rows.append((p["match_id"], made, p, m))

    best = {}
    for mid, made, p, m in rows:
        if mid not in best or made > best[mid][0]:
            best[mid] = (made, p, m)

    n = len(best)
    print(f"Jogos disputados com previsão anterior ao início: {n}")
    if n == 0:
        print("Nada para medir ainda. Rode de novo depois de algumas rodadas.")
        return
    if n < MIN_GAMES:
        print(f"AVISO: menos de {MIN_GAMES} jogos. Os números abaixo são ilustrativos, não conclusivos.\n")

    P = np.array([[p["p_away"], p["p_draw"], p["p_home"]] for _, p, _ in best.values()], dtype=float)
    y = np.array([0 if m["home_score"] < m["away_score"] else (1 if m["home_score"] == m["away_score"] else 2) for _, _, m in best.values()])
    onehot = np.eye(3)[y]

    prior = np.array([0.26, 0.27, 0.47])  # frequência histórica (A e B, 2020-2026)
    ll = lambda Q: -np.log(np.clip(Q[np.arange(n), y], 1e-9, 1)).mean()
    br = lambda Q: ((Q - onehot) ** 2).sum(axis=1).mean()
    print(f"Resultado:  modelo  log loss {ll(P):.4f}  Brier {br(P):.4f}")
    print(f"            prior   log loss {ll(np.tile(prior, (n, 1))):.4f}  Brier {br(np.tile(prior, (n, 1))):.4f}")
    print(f"            acerto do favorito do modelo: {(P.argmax(axis=1) == y).mean():.1%}\n")

    print("Calibração de P(mandante vence):")
    ph = P[:, 2]
    edges = [0, 0.35, 0.45, 0.55, 0.65, 1.01]
    print(f"  {'faixa':<14}{'jogos':>6}{'previsto':>10}{'observado':>11}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (ph >= lo) & (ph < hi)
        if mask.sum():
            print(f"  {lo:.0%}-{min(hi, 1):.0%}".ljust(16) + f"{mask.sum():>4}{ph[mask].mean():>10.1%}{(y[mask] == 2).mean():>11.1%}")

    po = [(p["p_over_2_5"], m["home_score"] + m["away_score"] >= 3) for _, p, m in best.values() if p["p_over_2_5"] is not None]
    if po:
        q = np.array([a for a, _ in po], dtype=float)
        o = np.array([b for _, b in po], dtype=float)
        print(f"\n3 gols ou mais ({len(po)} jogos): previsto médio {q.mean():.1%} | observado {o.mean():.1%}")


if __name__ == "__main__":
    main()
