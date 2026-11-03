"""Compara os jogos manuais da Série C (quadrangulares e final) com a Highlightly (usa cache, 0 chamadas)."""
import json
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from normalizers.highlightly import parse_score
from repositories.highlightly_repo import load_team_id_map

cache = Path(__file__).parent / ".cache" / "hl_matches_c.json"
hl = [m for m in json.loads(cache.read_text()) if not m["round"].startswith("Regular Season")]

team_map = load_team_id_map()
client = get_supabase_client()
cid = client.table("competitions").select("id").eq("code", "c").eq("season", 2026).execute().data[0]["id"]
names = {t["id"]: t["name"] for t in client.table("teams").select("id, name").execute().data}

manual = {
    (m["home_team_id"], m["away_team_id"]): (m["home_score"], m["away_score"])
    for m in client.table("matches").select("home_team_id, away_team_id, home_score, away_score")
    .eq("competition_id", cid).eq("provider", "manual").execute().data
}

ok, diffs, only_hl = 0, [], []
seen = set()
for m in hl:
    h, a = team_map.get(str(m["homeTeam"]["id"])), team_map.get(str(m["awayTeam"]["id"]))
    score = parse_score(m["state"]["score"]["current"])
    key = (h, a)
    if key not in manual:
        only_hl.append(f"{m['homeTeam']['name']} x {m['awayTeam']['name']}")
        continue
    seen.add(key)
    if manual[key] == score:
        ok += 1
    else:
        diffs.append(f"{names[h]} x {names[a]}: manual {manual[key]} | Highlightly {score}")

only_manual = [f"{names[h]} x {names[a]}" for (h, a) in manual if (h, a) not in seen]
print(f"Highlightly: {len(hl)} jogos | manual: {len(manual)} jogos")
print(f"Placares idênticos: {ok}")
for label, items in (("Placares diferentes", diffs), ("Só na Highlightly", only_hl), ("Só no manual", only_manual)):
    print(f"{label}: {len(items)}")
    for i in items:
        print("  -", i)
