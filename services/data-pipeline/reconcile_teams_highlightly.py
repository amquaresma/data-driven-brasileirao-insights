"""
Script de análise (não persiste nada): compara os times retornados
pela Highlightly para uma série com os times já existentes no nosso
banco (vindos da campeonato-brasileiro-api), tentando reconciliar por
nome normalizado.

Motivo de ser um passo separado e não-automático: os nomes divergem
entre fontes (acentuação, abreviações, sufixos como "DA GAMA"), e um
match errado significa misturar dados de dois times diferentes — um
erro caro de descobrir depois. Preferimos revisar manualmente os
casos ambíguos.

Uso:
    python reconcile_teams_highlightly.py a
"""

from __future__ import annotations

import sys
import unicodedata

from sources.highlightly import paginate_matches
from infrastructure.supabase import get_supabase_client


def normalize(name: str) -> str:
    """Remove acentos, deixa maiúsculo, remove espaços/hífens extras."""
    nfkd = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in nfkd if not unicodedata.combining(c))
    return without_accents.upper().replace("-", " ").strip()


def get_highlightly_teams(serie: str) -> dict[int, str]:
    """Retorna {external_id: name} de todos os times vistos nas partidas da série."""
    teams: dict[int, str] = {}
    for match in paginate_matches(serie, 2026):
        for side in ("homeTeam", "awayTeam"):
            team = match[side]
            teams[team["id"]] = team["name"]
    return teams


def get_our_teams() -> list[dict]:
    client = get_supabase_client()
    result = client.table("teams").select("id, name, short_name").execute()
    return result.data


def reconcile(serie: str) -> None:
    highlightly_teams = get_highlightly_teams(serie)
    our_teams = get_our_teams()

    our_by_normalized = {normalize(t["name"]): t for t in our_teams}

    exact_matches = []
    ambiguous = []

    for hl_id, hl_name in highlightly_teams.items():
        norm = normalize(hl_name)

        if norm in our_by_normalized:
            exact_matches.append((hl_id, hl_name, our_by_normalized[norm]))
            continue

        # tenta substring nos dois sentidos (ex: "Vasco" vs "Vasco DA Gama")
        candidates = [
            t for t in our_teams
            if normalize(t["name"]) in norm or norm in normalize(t["name"])
        ]
        if len(candidates) == 1:
            ambiguous.append((hl_id, hl_name, candidates, "substring único"))
        elif len(candidates) > 1:
            ambiguous.append((hl_id, hl_name, candidates, "múltiplos candidatos"))
        else:
            ambiguous.append((hl_id, hl_name, [], "nenhum candidato"))

    print(f"=== Série {serie.upper()} ===")
    print(f"Times na Highlightly: {len(highlightly_teams)}")
    print(f"Matches exatos (por nome normalizado): {len(exact_matches)}")
    print(f"Precisam de revisão: {len(ambiguous)}")
    print()

    if exact_matches:
        print("--- MATCHES EXATOS ---")
        for hl_id, hl_name, our_team in exact_matches:
            print(f"  Highlightly[{hl_id}] '{hl_name}' == nosso '{our_team['name']}' ({our_team['id']})")
        print()

    if ambiguous:
        print("--- PRECISAM REVISÃO ---")
        for hl_id, hl_name, candidates, reason in ambiguous:
            print(f"  Highlightly[{hl_id}] '{hl_name}' -- {reason}")
            for c in candidates:
                print(f"      candidato: '{c['name']}' (short: {c['short_name']}) -> {c['id']}")


if __name__ == "__main__":
    serie = sys.argv[1] if len(sys.argv) > 1 else "a"
    reconcile(serie)
