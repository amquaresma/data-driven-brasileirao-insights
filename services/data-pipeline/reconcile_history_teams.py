"""Reconcilia os times das temporadas históricas (usa cache, 0 chamadas). Dry-run por padrão."""
import argparse
import json
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from reconcile_teams_highlightly import normalize

CACHE = Path(__file__).parent / ".cache"
PROVIDER = "highlightly"

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
parser.add_argument("--link", action="append", default=[], help="HLID=UUID_DO_TIME (para casos em revisão)")
parser.add_argument("--create", action="append", default=[], help="HLID (cria como time novo, para casos em revisão)")
args = parser.parse_args()
links = dict(x.split("=", 1) for x in args.link)
creates = set(args.create)

hl = {}
for f in sorted(CACHE.glob("hl_hist_*.json")):
    for m in json.loads(f.read_text()):
        for side in ("homeTeam", "awayTeam"):
            hl[str(m[side]["id"])] = m[side]["name"]

client = get_supabase_client()
known = {
    r["external_id"]
    for r in client.table("team_external_ids").select("external_id").eq("provider", PROVIDER).execute().data
}
teams = client.table("teams").select("id, name").execute().data
by_norm = {}
for t in teams:
    by_norm.setdefault(normalize(t["name"]), []).append(t)

auto, review, new = [], [], []
for hid, name in hl.items():
    if hid in known:
        continue
    n = normalize(name)
    exact = by_norm.get(n, [])
    if len(exact) == 1:
        auto.append((hid, name, exact[0]))
        continue
    cands = [t for t in teams if normalize(t["name"]) in n or n in normalize(t["name"])]
    if exact or cands:
        review.append((hid, name, exact or cands))
    else:
        new.append((hid, name))

print(f"Times nas temporadas baixadas: {len(hl)} | já mapeados: {len(hl) - len(auto) - len(review) - len(new)}")
print(f"\nAUTO (nome igual a um time nosso): {len(auto)}")
for hid, name, t in auto:
    print(f"  [{hid}] {name} -> {t['name']}")
print(f"\nREVISÃO (nome parecido): {len(review)}")
for hid, name, cands in review:
    print(f"  [{hid}] {name}")
    for t in cands:
        print(f"      candidato: {t['name']}  {t['id']}")
print(f"\nNOVOS (nenhum parecido): {len(new)}")
for hid, name in new:
    print(f"  [{hid}] {name}")

if not args.apply:
    print("\nDry-run. Confira as listas e rode com --apply (use --link HLID=UUID ou --create HLID para os de revisão).")
    raise SystemExit(0)

def link(hid, team_id):
    client.table("team_external_ids").upsert(
        {"team_id": team_id, "provider": PROVIDER, "external_id": hid}, on_conflict="provider,external_id"
    ).execute()

def create(hid, name):
    team_id = client.table("teams").insert({"name": name}).execute().data[0]["id"]
    link(hid, team_id)

for hid, name, t in auto:
    link(hid, t["id"])
for hid, name in new:
    create(hid, name)
pending = []
for hid, name, _ in review:
    if hid in links:
        link(hid, links[hid])
    elif hid in creates:
        create(hid, name)
    else:
        pending.append(f"[{hid}] {name}")
print(f"\nGravado: {len(auto)} auto, {len(new)} novos. Revisão pendente: {len(pending)}")
for p in pending:
    print("  -", p)
