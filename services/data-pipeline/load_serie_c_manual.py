"""
Carga manual da Série C 2026 (a fonte automática deixou de cobrir as fases):
1ª fase (tabela), quadrangulares (tabelas calculadas dos jogos) e final.
Dados em manual/serie_c_2026_*.

Valida antes de gravar (só grava com --apply): pontos = 3V+E, saldo = GP-GS,
somas de gols/vitórias fecham, os 8 times dos quadrangulares são os 8
primeiros da 1ª fase, os finalistas são os líderes dos grupos e a final
dá Maringá 3 x 2. Os times já existem no banco: aqui só se mapeia o nome.

Uso:
    python load_serie_c_manual.py            # valida (dry-run)
    python load_serie_c_manual.py --apply
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from load_serie_d_groups import slugify
from load_serie_d_matches import LINE

DIR = Path(__file__).parent / "manual"
PROVIDER = "manual"

# nome na planilha -> nome do time no nosso banco (criado pelas outras fontes)
NAME_TO_DB = {
    "Ypiranga": "Ypiranga-RS",
    "Guarani": "Guaraní Campinas",
    "Maranhão": "Maranhão AC",
    "Barra-SC": "Barra",
    "Itabaiana-SE": "AO Itabaiana",
}

PHASES = {
    "primeira-fase": ("Primeira fase", "league", 1),
    "quadrangular-b": ("Quadrangular — Grupo B", "groups", 2),
    "quadrangular-c": ("Quadrangular — Grupo C", "groups", 2),
    "final": ("Final", "knockout", 3),
}
GROUP_OF = {"quadrangular-b": "Grupo B", "quadrangular-c": "Grupo C"}
FINAL_AGG = {"Maringá": 3, "Ferroviária": 2}


def parse_first_phase() -> list[dict]:
    rows = []
    with open(DIR / "serie_c_2026_primeira_fase.csv", encoding="utf-8", newline="") as f:
        for cols in csv.reader(f, delimiter=";"):
            if not cols or cols[0] in ("", "pos"):
                continue
            pos, team, pts, j, v, e, d, sg, gp, gs = (c.strip() for c in cols)
            rows.append({"pos": int(pos), "team": team, "pts": int(pts), "j": int(j), "v": int(v),
                         "e": int(e), "d": int(d), "sg": int(sg), "gp": int(gp), "gs": int(gs)})
    return rows


def parse_games() -> list[dict]:
    games, phase, leg = [], None, None
    for raw in (DIR / "serie_c_2026_jogos.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        sec = re.match(r"^\[([a-z-]+)(?:\|(\d))?\]$", line)
        if sec:
            phase, leg = sec.group(1), (int(sec.group(2)) if sec.group(2) else None)
            continue
        m = LINE.match(line)
        if not m:
            raise SystemExit(f"Linha não reconhecida: {line!r}")
        g = m.groupdict()
        games.append({"phase": phase, "leg": leg, "home": g["h"], "away": g["a"],
                      "hg": int(g["hg"]), "ag": int(g["ag"])})
    return games


def compute_table(games: list[dict]) -> list[dict]:
    t = defaultdict(lambda: {"j": 0, "v": 0, "e": 0, "d": 0, "gp": 0, "gs": 0})
    for g in games:
        for team, gf, ga in ((g["home"], g["hg"], g["ag"]), (g["away"], g["ag"], g["hg"])):
            r = t[team]
            r["j"] += 1
            r["gp"] += gf
            r["gs"] += ga
            if gf > ga:
                r["v"] += 1
            elif gf == ga:
                r["e"] += 1
            else:
                r["d"] += 1
    rows = []
    for team, r in t.items():
        r.update(team=team, pts=3 * r["v"] + r["e"], sg=r["gp"] - r["gs"])
        rows.append(r)
    rows.sort(key=lambda r: (-r["pts"], -r["v"], -r["sg"], -r["gp"]))
    return rows


def validate(first, games, errors, notes) -> dict:
    for r in first:
        w = f"1ª fase {r['team']}"
        if r["pts"] != 3 * r["v"] + r["e"]:
            errors.append(f"{w}: pontos {r['pts']} != 3V+E = {3 * r['v'] + r['e']}")
        if r["j"] != 19 or r["j"] != r["v"] + r["e"] + r["d"]:
            errors.append(f"{w}: jogos {r['j']} (esperado 19 = V+E+D)")
        if r["sg"] != r["gp"] - r["gs"]:
            errors.append(f"{w}: saldo {r['sg']} != GP-GS = {r['gp'] - r['gs']}")
    if len(first) != 20:
        errors.append(f"1ª fase: {len(first)} times (esperado 20)")
    if sum(r["gp"] for r in first) != sum(r["gs"] for r in first):
        errors.append("1ª fase: soma de gols pró != gols contra")
    if sum(r["v"] for r in first) != sum(r["d"] for r in first):
        errors.append("1ª fase: vitórias != derrotas")
    if sum(r["e"] for r in first) % 2:
        errors.append("1ª fase: número ímpar de empates")
    pts = [r["pts"] for r in first]
    if pts != sorted(pts, reverse=True):
        errors.append("1ª fase: times fora de ordem por pontos")

    tables = {}
    for phase, gname in GROUP_OF.items():
        gs = [g for g in games if g["phase"] == phase]
        if len(gs) != 12:
            errors.append(f"{gname}: {len(gs)} jogos (esperado 12)")
        t = compute_table(gs)
        if len(t) != 4 or any(r["j"] != 6 for r in t):
            errors.append(f"{gname}: esperados 4 times com 6 jogos cada")
        tables[phase] = t
        for a, b in zip(t, t[1:]):
            if (a["pts"], a["v"], a["sg"]) == (b["pts"], b["v"], b["sg"]):
                notes.append(f"[desempate] {gname}: {a['team']} ({a['gp']} GP) e {b['team']} ({b['gp']} GP) "
                             "iguais em pontos, vitórias e saldo; ordenados por gols pró (critério não confirmado na fonte)")

    quad = {r["team"] for t in tables.values() for r in t}
    top8 = {r["team"] for r in first[:8]}
    if quad != top8:
        errors.append(f"quadrangulares != 8 primeiros da 1ª fase: {sorted(quad ^ top8)}")

    fin = [g for g in games if g["phase"] == "final"]
    if len(fin) != 2:
        errors.append(f"final: {len(fin)} jogos (esperado 2)")
    elif len(tables) == 2:
        leaders = {t[0]["team"] for t in tables.values()}
        if {t for g in fin for t in (g["home"], g["away"])} != leaders:
            errors.append(f"final: finalistas != líderes dos grupos {sorted(leaders)}")
        agg = defaultdict(int)
        for g in fin:
            agg[g["home"]] += g["hg"]
            agg[g["away"]] += g["ag"]
        if dict(agg) != FINAL_AGG:
            errors.append(f"final: agregado {dict(agg)} != {FINAL_AGG}")
    return tables


def resolve_teams(client, names, errors) -> dict[str, str]:
    out = {}
    for n in sorted(names):
        db_name = NAME_TO_DB.get(n, n)
        res = client.table("teams").select("id").eq("name", db_name).execute().data
        if len(res) != 1:
            errors.append(f"time {n!r} (banco: {db_name!r}): {len(res)} resultados (esperado 1)")
        else:
            out[n] = res[0]["id"]
    return out


def apply(client, cid, first, games, tables, team_ids) -> None:
    phase_ids = {}
    for slug, (name, ptype, order) in PHASES.items():
        res = client.table("phases").upsert(
            {"competition_id": cid, "slug": slug, "name": name, "phase_type": ptype, "phase_order": order},
            on_conflict="competition_id,slug",
        ).execute()
        phase_ids[slug] = res.data[0]["id"]

    group_ids = {}
    for slug, gname in GROUP_OF.items():
        found = client.table("groups").select("id").eq("competition_id", cid).eq("name", gname).execute().data
        if found:
            gid = found[0]["id"]
            client.table("groups").update({"phase_id": phase_ids[slug]}).eq("id", gid).execute()
        else:
            gid = client.table("groups").insert({
                "competition_id": cid, "external_id": f"manual-c-{gname[-1].lower()}",
                "name": gname, "phase_id": phase_ids[slug],
            }).execute().data[0]["id"]
        group_ids[slug] = gid

    removed = client.table("matches").delete().eq("competition_id", cid).eq("provider", "campeonato-brasileiro-api").execute()
    print(f"Jogos antigos da fonte automática removidos: {len(removed.data)}")

    def standing(slug, gid, table_name, pos, r, team):
        return {
            "competition_id": cid, "phase_id": phase_ids[slug], "group_id": gid,
            "team_id": team_ids[team], "table_name": table_name, "position": pos,
            "points": r["pts"], "matches_played": r["j"], "wins": r["v"], "draws": r["e"],
            "losses": r["d"], "goals_for": r["gp"], "goals_against": r["gs"],
            "goal_difference": r["sg"], "source_provider": PROVIDER,
        }

    payloads = [standing("primeira-fase", None, "Primeira fase", r["pos"], r, r["team"]) for r in first]
    for slug, rows in tables.items():
        for pos, r in enumerate(rows, start=1):
            payloads.append(standing(slug, group_ids[slug], PHASES[slug][0], pos, r, r["team"]))
    client.table("standings_entries").upsert(payloads, on_conflict="competition_id,phase_id,team_id").execute()

    rows, seq = [], defaultdict(int)
    for g in games:
        sh, sa = slugify(g["home"]), slugify(g["away"])
        if g["phase"] == "final":
            key = f"final:01:{'-'.join(sorted((sh, sa)))}"
            ext = f"c2026-final-{sh}-{sa}-l{g['leg']}"
        else:
            seq[g["phase"]] += 1
            n = seq[g["phase"]]
            key, ext = f"{g['phase']}:{n:02d}", f"c2026-{g['phase']}-{n:02d}-{sh}-{sa}"
        rows.append({
            "provider": PROVIDER, "external_id": ext, "competition_id": cid,
            "phase_id": phase_ids[g["phase"]],
            "home_team_id": team_ids[g["home"]], "away_team_id": team_ids[g["away"]],
            "started": True, "status": "Finished", "status_code": "Finished",
            "home_score": g["hg"], "away_score": g["ag"], "tie_key": key, "leg": g["leg"],
        })
    client.table("matches").upsert(rows, on_conflict="provider,external_id").execute()
    print(f"Gravado: {len(payloads)} linhas de classificação e {len(rows)} jogos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga manual da Série C 2026.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    first, games = parse_first_phase(), parse_games()
    errors, notes = [], []
    tables = validate(first, games, errors, notes)

    client = get_supabase_client()
    comp = client.table("competitions").select("id").eq("code", "c").eq("season", 2026).limit(1).execute().data
    if not comp:
        raise SystemExit("Competição da Série C 2026 não existe.")
    cid = comp[0]["id"]

    names = {r["team"] for r in first} | {t for g in games for t in (g["home"], g["away"])}
    team_ids = resolve_teams(client, names, errors)

    print(f"{len(first)} times na 1ª fase e {len(games)} jogos lidos.")
    for slug, rows in tables.items():
        print(f"  {GROUP_OF[slug]}: " + " > ".join(f"{r['team']} {r['pts']}" for r in rows))
    for n in notes:
        print(" ", n)
    stale = client.table("matches").select("id", count="exact").eq("competition_id", cid).eq("provider", "campeonato-brasileiro-api").execute()
    print(f"  Jogos antigos da fonte automática que serão removidos no --apply: {stale.count}")

    if errors:
        print(f"\n{len(errors)} inconsistência(s). Nada foi gravado:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print("Validação OK.")
    if args.apply:
        apply(client, cid, first, games, tables, team_ids)
    else:
        print("Dry-run: rode com --apply para gravar.")
