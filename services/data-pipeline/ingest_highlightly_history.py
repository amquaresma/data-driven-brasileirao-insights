"""Grava as temporadas históricas de A e B (usa cache, 0 chamadas). Idempotente."""
import json
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from normalizers.highlightly import normalize_match, normalize_round
from repositories.highlightly_repo import create_round, load_round_id_map, load_team_id_map

CACHE = Path(__file__).parent / ".cache"
client = get_supabase_client()
team_map = load_team_id_map()


def ensure_competition(serie: str, season: int) -> str:
    found = client.table("competitions").select("id").eq("code", serie).eq("season", season).limit(1).execute().data
    if found:
        return found[0]["id"]
    return client.table("competitions").insert({
        "code": serie, "season": season,
        "name": f"Campeonato Brasileiro Série {serie.upper()} {season}",
        "slug": f"brasileirao-serie-{serie}", "sport": "futebol", "grouped": False,
        "phase_description": "Pontos Corridos", "source_provider": "highlightly",
    }).execute().data[0]["id"]


for f in sorted(CACHE.glob("hl_hist_*.json")):
    _, serie, season = f.stem.split("_")[1:]
    season = int(season)
    matches = json.loads(f.read_text())
    cid = ensure_competition(serie, season)
    rounds = load_round_id_map(cid)

    rows, skipped = [], 0
    for hm in matches:
        home = team_map.get(str(hm["homeTeam"]["id"]))
        away = team_map.get(str(hm["awayTeam"]["id"]))
        if home is None or away is None:
            skipped += 1
            continue
        rd = normalize_round(hm)
        round_id = None
        if rd["number"] is not None:
            round_id = rounds.get(rd["number"])
            if round_id is None:
                round_id = create_round(competition_id=cid, group_id=None, round_data=rd)
                rounds[rd["number"]] = round_id
        row = normalize_match(hm)
        row.update(competition_id=cid, round_id=round_id, home_team_id=home, away_team_id=away)
        rows.append(row)

    for i in range(0, len(rows), 100):
        saved = client.table("matches").upsert(rows[i:i + 100], on_conflict="provider,external_id").execute().data
        client.table("match_external_ids").upsert(
            [{"match_id": r["id"], "provider": "highlightly", "external_id": r["external_id"]} for r in saved],
            on_conflict="provider,external_id",
        ).execute()
    fin = sum(1 for r in rows if (r["status"] or "") == "Finished")
    print(f"{serie.upper()} {season}: {len(rows)} jogos gravados ({fin} finalizados), {skipped} pulados por time sem reconciliação")
