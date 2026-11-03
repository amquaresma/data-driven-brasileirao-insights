"""
Ingestão de partidas da Highlightly para uma série/temporada,
reconciliando com o que já existe no banco.

Carrega reconciliações de time, partidas e rodadas já existentes em
lote (poucas queries), evitando uma ida ao banco por partida.

Uso:
    python ingest_highlightly.py a
    python ingest_highlightly.py a --season 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from infrastructure.supabase import get_supabase_client

from sources.highlightly import paginate_matches, get_league_id
from sources.exceptions import BrasileiraoSourceError
from normalizers.highlightly import normalize_match, normalize_round
from repositories.highlightly_repo import (
    resolve_competition_id,
    load_team_id_map,
    load_existing_matches,
    load_round_id_map,
    create_round,
    link_match,
    create_match,
    update_match_live_fields,
)


def ingest_matches(serie: str, season: int = 2026, use_cache: bool = False) -> None:
    league_id = get_league_id(serie)
    if league_id is None:
        print(f"Série '{serie}' não é coberta pela Highlightly. Nada a fazer.")
        return

    print(f"Buscando partidas da Highlightly para série '{serie}' (league {league_id}, temporada {season})...")

    competition_id = resolve_competition_id(serie, season, league_id)

    # Séries com fases (C): a 1ª fase fica ligada à fase "Primeira fase".
    phase = (
        get_supabase_client().table("phases").select("id")
        .eq("competition_id", competition_id).eq("slug", "primeira-fase").limit(1).execute().data
    )
    phase_id = phase[0]["id"] if phase else None

    print("Carregando reconciliações em lote (times, partidas, rodadas existentes)...")
    team_id_map = load_team_id_map()
    existing_matches = load_existing_matches(competition_id)
    round_id_map = load_round_id_map(competition_id)

    cache = Path(__file__).parent / ".cache" / f"hl_matches_{serie}.json"
    if use_cache and cache.exists():
        all_matches = json.loads(cache.read_text())
        print(f"Usando cache local ({cache.name}), 0 chamadas à API.")
    else:
        all_matches = list(paginate_matches(serie, season))

    # Quadrangulares, mata-mata e final são carregados à mão: aqui só a fase de pontos corridos.
    regular = [m for m in all_matches if str(m.get("round", "")).startswith("Regular Season")]
    if len(regular) != len(all_matches):
        print(f"Ignorando {len(all_matches) - len(regular)} jogos de fases que não são Regular Season.")
    all_matches = regular
    total = len(all_matches)
    print(f"{total} partidas retornadas pela Highlightly. Processando...")

    linked = 0
    created = 0
    skipped_no_team = []

    for i, hl_match in enumerate(all_matches, start=1):
        home_hl_id = str(hl_match["homeTeam"]["id"])
        away_hl_id = str(hl_match["awayTeam"]["id"])

        home_team_id = team_id_map.get(home_hl_id)
        away_team_id = team_id_map.get(away_hl_id)

        if home_team_id is None or away_team_id is None:
            skipped_no_team.append(
                (hl_match["homeTeam"]["name"], hl_match["awayTeam"]["name"])
            )
            continue

        round_data = normalize_round(hl_match)
        round_number = round_data.get("number")
        round_id = None
        if round_number is not None:
            round_id = round_id_map.get(round_number)
            if round_id is None:
                round_id = create_round(
                    competition_id=competition_id, group_id=None, round_data=round_data
                )
                round_id_map[round_number] = round_id

        match_data = normalize_match(hl_match)
        if phase_id:
            match_data["phase_id"] = phase_id
        pair_key = (home_team_id, away_team_id)
        candidates = existing_matches.get(pair_key, [])

        if len(candidates) == 1:
            link_match(candidates[0], match_data["external_id"])
            update_match_live_fields(candidates[0], match_data)
            linked += 1
        else:
            match_id = create_match(
                match_data=match_data,
                competition_id=competition_id,
                round_id=round_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            )
            link_match(match_id, match_data["external_id"])
            existing_matches.setdefault(pair_key, []).append(match_id)
            created += 1

        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] processadas...")

    print()
    print(f"Partidas linkadas a registros existentes: {linked}")
    print(f"Partidas novas criadas: {created}")
    if skipped_no_team:
        print(f"Partidas puladas por falta de reconciliação de time: {len(skipped_no_team)}")
        for home, away in skipped_no_team[:10]:
            print(f"  {home} x {away}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão de partidas da Highlightly.")
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--use-cache", action="store_true")
    args = parser.parse_args()

    try:
        ingest_matches(args.serie, args.season, args.use_cache)
    except BrasileiraoSourceError as exc:
        print(f"Erro ao consumir a fonte: [{exc.code}] {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
