"""
Carga manual dos jogos eliminatórios da Série D 2026 (2ª fase até a final,
mais playoffs de acesso). Dados em manual/serie_d_2026_jogos.txt.

Valida antes de gravar (só grava com --apply):
  - todo time existe na carga dos grupos (provider 'manual');
  - todo confronto tem ida e volta; se a fonte repete o mandante da ida na
    volta, inverte o mando MANTENDO os gols com cada time e avisa;
  - classificado = agregado, depois pênaltis; empate sem pênaltis só passa
    se estiver em MANUAL_ADVANCE (nada é inventado);
  - os classificados de cada fase são exatamente os times da fase seguinte;
  - campeão e playoffs conferem.

Uso:
    python load_serie_d_matches.py            # valida (dry-run)
    python load_serie_d_matches.py --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from load_serie_d_groups import slugify

DATA_FILE = Path(__file__).parent / "manual" / "serie_d_2026_jogos.txt"
PROVIDER = "manual"

PHASES = {
    "segunda-fase": ("Segunda fase", 2),
    "terceira-fase": ("Terceira fase", 3),
    "oitavas": ("Oitavas de final", 4),
    "quartas": ("Quartas de final", 5),
    "semifinal": ("Semifinal", 7),
    "final": ("Final", 8),
    "playoff-acesso": ("Playoff de acesso", 6),
}
CHAIN = ["segunda-fase", "terceira-fase", "oitavas", "quartas", "semifinal", "final"]

ALIASES = {"São José-RS": "São José"}  # nos grupos o time aparece como "São José"

# Lacunas conhecidas da fonte (não inventamos):
#  - 32º confronto da 2ª fase (Água Santa x Velo Clube) ausente; Velo Clube avançou.
KNOWN_GAPS = {"segunda-fase": {"Velo Clube"}}
#  - pênaltis do playoff Goiatuba x São José-RS ausentes; a fonte diz que São José passou.
MANUAL_ADVANCE = {("playoff-acesso", frozenset({"Goiatuba", "São José"})): "São José"}

CHAMPION, CHAMPION_AGG = "Uberlândia", (3, 1)
PLAYOFF_WINNERS = {"Nacional-AM", "São José"}

LINE = re.compile(
    r"^(?P<h>.+?) (?P<hg>\d+)(?: \((?P<hp>\d+)\))? x (?:\((?P<ap>\d+)\) )?(?P<ag>\d+) (?P<a>.+)$"
)


def parse() -> list[dict]:
    recs, phase, leg = [], None, None
    for raw in DATA_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        sec = re.match(r"^\[(.+)\|(\d)\]$", line)
        if sec:
            phase, leg = sec.group(1), int(sec.group(2))
            continue
        m = LINE.match(line)
        if not m:
            raise SystemExit(f"Linha não reconhecida: {line!r}")
        g = m.groupdict()
        recs.append({
            "phase": phase, "leg": leg,
            "home": ALIASES.get(g["h"], g["h"]), "away": ALIASES.get(g["a"], g["a"]),
            "hg": int(g["hg"]), "ag": int(g["ag"]),
            "hp": int(g["hp"]) if g["hp"] else None, "ap": int(g["ap"]) if g["ap"] else None,
        })
    return recs


def normalize(recs: list[dict], notes: list[str], errors: list[str]) -> None:
    first = {(r["phase"], frozenset((r["home"], r["away"]))): r for r in recs if r["leg"] == 1}
    for r in recs:
        if r["leg"] != 2:
            continue
        ida = first.get((r["phase"], frozenset((r["home"], r["away"]))))
        if ida is None:
            errors.append(f"{r['phase']}: volta sem ida: {r['home']} x {r['away']}")
        elif r["home"] == ida["home"]:
            notes.append(f"[mando invertido] {r['phase']}: {r['home']} x {r['away']} (a fonte repete o mandante da ida)")
            r["home"], r["away"] = r["away"], r["home"]
            r["hg"], r["ag"] = r["ag"], r["hg"]
            r["hp"], r["ap"] = r["ap"], r["hp"]
    legs = defaultdict(set)
    for r in recs:
        legs[(r["phase"], frozenset((r["home"], r["away"])))].add(r["leg"])
    for (phase, pair), ls in legs.items():
        if ls != {1, 2}:
            errors.append(f"{phase}: confronto sem ida e volta: {sorted(pair)}")


def winners(recs: list[dict], errors: list[str]) -> dict[str, dict]:
    ties = defaultdict(list)
    for r in recs:
        ties[(r["phase"], frozenset((r["home"], r["away"])))].append(r)
    out = defaultdict(dict)
    for (phase, pair), games in ties.items():
        goals, pens = defaultdict(int), defaultdict(lambda: None)
        for r in games:
            goals[r["home"]] += r["hg"]
            goals[r["away"]] += r["ag"]
            if r["hp"] is not None:
                pens[r["home"]], pens[r["away"]] = r["hp"], r["ap"]
        a, b = sorted(pair)
        if goals[a] != goals[b]:
            win = a if goals[a] > goals[b] else b
        elif pens[a] is not None and pens[a] != pens[b]:
            win = a if pens[a] > pens[b] else b
        elif (phase, pair) in MANUAL_ADVANCE:
            win = MANUAL_ADVANCE[(phase, pair)]
        else:
            errors.append(f"{phase}: {a} x {b} empatado no agregado e sem pênaltis")
            continue
        out[phase][pair] = {"winner": win, "agg": (goals[a], goals[b]), "teams": (a, b)}
    return out


def check_progression(recs, results, errors) -> None:
    teams_in = lambda p: {t for r in recs if r["phase"] == p for t in (r["home"], r["away"])}
    for cur, nxt in zip(CHAIN, CHAIN[1:]):
        got = {v["winner"] for v in results[cur].values()} | KNOWN_GAPS.get(cur, set())
        want = teams_in(nxt)
        if got != want:
            errors.append(
                f"{cur} -> {nxt}: classificados que não aparecem na fase seguinte: {sorted(got - want)}; "
                f"times da fase seguinte sem classificação anterior: {sorted(want - got)}"
            )
    final = next(iter(results["final"].values()))
    agg = dict(zip(final["teams"], final["agg"]))
    if final["winner"] != CHAMPION or sorted(agg.values(), reverse=True) != list(CHAMPION_AGG):
        errors.append(f"final: esperado {CHAMPION} {CHAMPION_AGG}, veio {final['winner']} {agg}")
    pw = {v["winner"] for v in results["playoff-acesso"].values()}
    if pw != PLAYOFF_WINNERS:
        errors.append(f"playoffs: esperado {sorted(PLAYOFF_WINNERS)}, veio {sorted(pw)}")


def apply(recs: list[dict]) -> None:
    client = get_supabase_client()
    comp = client.table("competitions").select("id").eq("code", "d").eq("season", 2026).limit(1).execute()
    if not comp.data:
        raise SystemExit("Competição da Série D 2026 não existe.")
    cid = comp.data[0]["id"]

    phase_ids = {}
    for slug, (name, order) in PHASES.items():
        res = client.table("phases").upsert(
            {"competition_id": cid, "slug": slug, "name": name, "phase_type": "knockout", "phase_order": order},
            on_conflict="competition_id,slug",
        ).execute()
        phase_ids[slug] = res.data[0]["id"]

    team_ids = {
        r["external_id"]: r["team_id"]
        for r in client.table("team_external_ids").select("external_id, team_id").eq("provider", PROVIDER).execute().data
    }
    seq: dict = {}
    for r in recs:
        key = (r["phase"], frozenset((r["home"], r["away"])))
        if r["leg"] == 1 and key not in seq:
            seq[key] = sum(1 for k in seq if k[0] == r["phase"]) + 1

    rows = []
    for r in recs:
        sh, sa = slugify(r["home"]), slugify(r["away"])
        rows.append({
            "provider": PROVIDER,
            "external_id": f"d2026-{r['phase']}-{sh}-{sa}-l{r['leg']}",
            "competition_id": cid, "phase_id": phase_ids[r["phase"]],
            "home_team_id": team_ids[sh], "away_team_id": team_ids[sa],
            "started": True, "status": "Finished", "status_code": "Finished",
            "home_score": r["hg"], "away_score": r["ag"],
            "penalties_home": r["hp"], "penalties_away": r["ap"],
            "tie_key": f"{r['phase']}:{seq[(r['phase'], frozenset((r['home'], r['away'])))]:02d}:{'-'.join(sorted((sh, sa)))}", "leg": r["leg"],
        })
    for i in range(0, len(rows), 100):
        client.table("matches").upsert(rows[i:i + 100], on_conflict="provider,external_id").execute()
    print(f"Gravado: {len(rows)} jogos em {len(PHASES)} fases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga manual dos jogos da Série D.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    recs = parse()
    notes, errors = [], []
    normalize(recs, notes, errors)
    results = winners(recs, errors)

    client = get_supabase_client()
    known = {r["external_id"] for r in client.table("team_external_ids").select("external_id").eq("provider", PROVIDER).execute().data}
    for t in sorted({t for r in recs for t in (r["home"], r["away"])}):
        if slugify(t) not in known:
            errors.append(f"time não encontrado na carga dos grupos: {t}")

    if not errors:
        check_progression(recs, results, errors)

    print(f"{len(recs)} jogos lidos em {len({r['phase'] for r in recs})} fases.")
    for n in notes:
        print(" ", n)
    if errors:
        print(f"\n{len(errors)} inconsistência(s). Nada foi gravado:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    print("Validação OK (classificados de cada fase batem com a fase seguinte, campeão e playoffs conferem).")
    if args.apply:
        apply(recs)
    else:
        print("Dry-run: rode com --apply para gravar.")
