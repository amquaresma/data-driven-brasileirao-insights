"""
Carga manual da fase de grupos da Série D 2026 (a fonte automática deixou
de cobrir essa fase). Dados em manual/serie_d_2026_grupos.csv.

Valida antes de gravar: pontos = 3V+E, jogos = V+E+D, saldo = GP-GS, e por
grupo: 6 times, soma de gols pró = gols contra, vitórias = derrotas, empates
em número par, ordem por pontos. Só grava com --apply.

Uso:
    python load_serie_d_groups.py            # só valida (dry-run)
    python load_serie_d_groups.py --apply    # valida e grava
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from infrastructure.supabase import get_supabase_client

DATA_FILE = Path(__file__).parent / "manual" / "serie_d_2026_grupos.csv"
PROVIDER = "manual"
EXPECTED_GROUPS = 16
TEAMS_PER_GROUP = 6
GAMES_PER_TEAM = 10


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def parse_rows() -> list[dict]:
    rows = []
    with open(DATA_FILE, encoding="utf-8", newline="") as f:
        for lineno, cols in enumerate(csv.reader(f, delimiter=";"), start=1):
            if not cols or cols[0].startswith("#") or cols[0] == "grupo":
                continue
            group, team, pts, j, v, e, d, sg, gp, gs = (c.strip() for c in cols)
            derived = gs == "?"
            gp_i, sg_i = int(gp), int(sg)
            rows.append(
                {
                    "line": lineno, "group": group, "team": team,
                    "pts": int(pts), "j": int(j), "v": int(v), "e": int(e), "d": int(d),
                    "sg": sg_i, "gp": gp_i,
                    "gs": gp_i - sg_i if derived else int(gs),
                    "gs_derived": derived,
                }
            )
    return rows


def validate(rows: list[dict]) -> list[str]:
    errors = []
    for r in rows:
        where = f"linha {r['line']} ({r['group']} {r['team']})"
        if r["pts"] != 3 * r["v"] + r["e"]:
            errors.append(f"{where}: pontos {r['pts']} != 3V+E = {3 * r['v'] + r['e']}")
        if r["j"] != r["v"] + r["e"] + r["d"]:
            errors.append(f"{where}: jogos {r['j']} != V+E+D = {r['v'] + r['e'] + r['d']}")
        if r["j"] != GAMES_PER_TEAM:
            errors.append(f"{where}: esperados {GAMES_PER_TEAM} jogos, veio {r['j']}")
        if r["sg"] != r["gp"] - r["gs"]:
            errors.append(f"{where}: saldo {r['sg']} != GP-GS = {r['gp'] - r['gs']}")

    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r)

    expected = {f"A{i}" for i in range(1, EXPECTED_GROUPS + 1)}
    if set(by_group) != expected:
        errors.append(f"grupos esperados A1..A{EXPECTED_GROUPS}, vieram {sorted(by_group)}")

    for g, items in by_group.items():
        if len(items) != TEAMS_PER_GROUP:
            errors.append(f"{g}: {len(items)} times (esperado {TEAMS_PER_GROUP})")
        if sum(i["gp"] for i in items) != sum(i["gs"] for i in items):
            errors.append(
                f"{g}: soma de gols pró ({sum(i['gp'] for i in items)}) != "
                f"gols contra ({sum(i['gs'] for i in items)})"
            )
        if sum(i["v"] for i in items) != sum(i["d"] for i in items):
            errors.append(f"{g}: vitórias != derrotas")
        if sum(i["e"] for i in items) % 2:
            errors.append(f"{g}: número ímpar de empates")
        pts = [i["pts"] for i in items]
        if pts != sorted(pts, reverse=True):
            errors.append(f"{g}: times fora de ordem por pontos")

    slugs = defaultdict(list)
    for r in rows:
        slugs[slugify(r["team"])].append(f"{r['group']} {r['team']}")
    for slug, names in slugs.items():
        if len(names) > 1:
            errors.append(f"nome repetido ou ambíguo: {names}")
    return errors


def apply(rows: list[dict]) -> None:
    client = get_supabase_client()

    comp = (
        client.table("competitions").select("id")
        .eq("code", "d").eq("season", 2026).limit(1).execute()
    )
    if not comp.data:
        raise SystemExit("Competição da Série D 2026 não existe. Rode ingest.py standings d antes.")
    competition_id = comp.data[0]["id"]

    phase = client.table("phases").upsert(
        {
            "competition_id": competition_id, "slug": "fase-de-grupos",
            "name": "Fase de grupos", "phase_type": "groups", "phase_order": 1,
        },
        on_conflict="competition_id,slug",
    ).execute()
    phase_id = phase.data[0]["id"]

    group_ids = {}
    for g in sorted({r["group"] for r in rows}, key=lambda x: int(x[1:])):
        res = client.table("groups").upsert(
            {
                "competition_id": competition_id, "external_id": f"manual-{g.lower()}",
                "name": f"Grupo {g}", "phase_id": phase_id,
            },
            on_conflict="competition_id,external_id",
        ).execute()
        group_ids[g] = res.data[0]["id"]

    existing = {
        r["external_id"]: r["team_id"]
        for r in client.table("team_external_ids")
        .select("external_id, team_id").eq("provider", PROVIDER).execute().data
    }

    created = 0
    position = defaultdict(int)
    payloads = []
    for r in rows:
        slug = slugify(r["team"])
        team_id = existing.get(slug)
        if team_id is None:
            team_id = client.table("teams").insert({"name": r["team"]}).execute().data[0]["id"]
            client.table("team_external_ids").insert(
                {"team_id": team_id, "provider": PROVIDER, "external_id": slug}
            ).execute()
            existing[slug] = team_id
            created += 1

        position[r["group"]] += 1
        payloads.append(
            {
                "competition_id": competition_id,
                "phase_id": phase_id,
                "group_id": group_ids[r["group"]],
                "team_id": team_id,
                "table_name": f"Grupo {r['group']}",
                "position": position[r["group"]],
                "points": r["pts"],
                "matches_played": r["j"],
                "wins": r["v"],
                "draws": r["e"],
                "losses": r["d"],
                "goals_for": r["gp"],
                "goals_against": r["gs"],
                "goal_difference": r["sg"],
                "source_provider": PROVIDER,
            }
        )

    client.table("standings_entries").upsert(
        payloads, on_conflict="competition_id,phase_id,team_id"
    ).execute()
    print(f"Gravado: {len(group_ids)} grupos, {len(payloads)} linhas de classificação, {created} times novos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga manual da fase de grupos da Série D.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    rows = parse_rows()
    errors = validate(rows)
    print(f"{len(rows)} linhas e {len({r['group'] for r in rows})} grupos lidos.")
    for r in rows:
        if r["gs_derived"]:
            print(f"  [derivado] {r['group']} {r['team']}: gols sofridos = GP - SG = {r['gs']}")

    if errors:
        print(f"\n{len(errors)} inconsistência(s). Nada foi gravado:")
        for err in errors:
            print("  -", err)
        sys.exit(1)

    print("Validação OK.")
    if args.apply:
        apply(rows)
    else:
        print("Dry-run: rode com --apply para gravar.")
