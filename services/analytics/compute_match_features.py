"""
Calcula e grava match_features (features pré-jogo + alvos) das partidas finalizadas.
Percorre todas as temporadas da série em ordem cronológica (o Elo é contínuo).

Uso:
    python compute_match_features.py a
"""

from __future__ import annotations

import argparse
from collections import Counter

from calculations.match_features import FeatureMatch, build_match_features
from infrastructure.supabase import get_supabase_client

PAGE = 1000


def fetch_matches(client, competition_id: str) -> list[dict]:
    out, offset = [], 0
    while True:
        page = (
            client.table("matches")
            .select("id, competition_id, match_date, match_time, home_team_id, away_team_id, home_score, away_score, status")
            .eq("competition_id", competition_id)
            .not_.is_("home_score", "null")
            .not_.is_("away_score", "null")
            .not_.is_("match_date", "null")
            .order("match_date")
            .order("id")
            .range(offset, offset + PAGE - 1)
            .execute()
            .data
        )
        out.extend(page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def main(serie: str) -> None:
    client = get_supabase_client()
    comps = client.table("competitions").select("id, season").eq("code", serie).order("season").execute().data

    matches: list[FeatureMatch] = []
    for comp in comps:
        for m in fetch_matches(client, comp["id"]):
            status = m["status"] or ""
            if "Finish" not in status and status != "finished":
                continue
            matches.append(FeatureMatch(
                m["id"], m["competition_id"], m["match_date"], m["match_time"],
                m["home_team_id"], m["away_team_id"], m["home_score"], m["away_score"],
            ))

    dupes = [k for k, n in Counter((m.match_date, m.home_team_id, m.away_team_id) for m in matches).items() if n > 1]
    if dupes:
        print(f"ATENÇÃO: {len(dupes)} confrontos repetidos na mesma data (possível duplicata).")

    rows = build_match_features(matches)
    for i in range(0, len(rows), 200):
        client.table("match_features").upsert(rows[i:i + 200], on_conflict="match_id").execute()

    ok = [r for r in rows if r["min_history_ok"]]
    res = Counter(r["result"] for r in ok)
    print(f"Série {serie.upper()}: {len(rows)} jogos gravados, {len(ok)} com histórico mínimo.")
    if ok:
        print(f"  Resultado (com histórico): casa {res['H'] / len(ok):.0%} | empate {res['D'] / len(ok):.0%} | fora {res['A'] / len(ok):.0%}")
        print(f"  Over 2.5: {sum(r['over_2_5'] for r in ok) / len(ok):.0%} | gols/jogo: {sum(r['total_goals'] for r in ok) / len(ok):.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula match_features.")
    parser.add_argument("serie", choices=["a", "b"])
    main(parser.parse_args().serie)
