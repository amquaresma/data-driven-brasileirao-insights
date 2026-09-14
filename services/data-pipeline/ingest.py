"""
Orquestra a ingestão de dados do Campeonato Brasileiro:

    fetch (sources) -> normalize (normalizers) -> persist (repositories)

Uso:
    python ingest.py standings a
    python ingest.py standings d --group A1
    python ingest.py rounds a
    python ingest.py rounds d --group A1
"""

from __future__ import annotations

import argparse
import sys

from sources.campeonato_brasileiro import get_standings, get_rounds, Serie
from sources.exceptions import BrasileiraoSourceError
from normalizers.campeonato_brasileiro import (
    normalize_competition,
    normalize_team,
    normalize_groups,
    normalize_standings_entries,
    normalize_round,
    normalize_match,
)
from repositories.supabase_repo import (
    upsert_competition,
    upsert_group,
    upsert_team,
    upsert_standings_entry,
    upsert_round,
    upsert_match,
)


def ingest_standings(serie: Serie, *, group: str | None = None) -> None:
    print(f"Buscando standings da série '{serie}'" + (f" (grupo {group})" if group else "") + "...")

    raw = get_standings(serie, group=group)

    competition = normalize_competition(raw)
    competition_id = upsert_competition(competition)
    print(f"  Competição: {competition['name']} -> {competition_id}")
    print(f"  Agrupada (fase atual): {competition['grouped']}")

    groups = normalize_groups(raw)
    group_id_by_external_id: dict[str, str] = {}
    for grp in groups:
        group_id = upsert_group(competition_id, grp["external_id"], grp["name"])
        group_id_by_external_id[grp["external_id"]] = group_id
        print(f"  Grupo: {grp['name']} -> {group_id}")

    entries = normalize_standings_entries(raw)
    print(f"  {len(entries)} entradas de classificação encontradas.")

    for entry in entries:
        team_data, external_id_data = normalize_team(entry["team"])
        team_id = upsert_team(team_data, external_id_data)

        group_id = None
        if entry["group_external_id"] is not None:
            group_id = group_id_by_external_id.get(entry["group_external_id"])

        upsert_standings_entry(
            competition_id=competition_id,
            team_id=team_id,
            group_id=group_id,
            entry=entry,
        )
        group_label = f" ({entry['table_name']})" if entry["group_external_id"] else ""
        print(f"    [{entry['position']:>2}] {team_data['name']:<20} {entry['points']} pts{group_label}")

    print("Ingestão de standings concluída com sucesso.")


def ingest_rounds(serie: Serie, *, group: str | None = None) -> None:
    print(f"Buscando rounds da série '{serie}'" + (f" (grupo {group})" if group else "") + "...")

    raw = get_rounds(serie, group=group)

    competition = normalize_competition({"competition": raw["competition"], "grouped": raw.get("grouped")})
    competition_id = upsert_competition(competition)
    print(f"  Competição: {competition['name']} -> {competition_id}")

    total_matches = 0

    for round_obj in raw.get("rounds", []):
        if round_obj.get("number") is None:
            print(f"  Round sem numeração (fase provavelmente sem classificação por rodada) — pulando.")
            continue

        group_id = None
        if round_obj.get("groupId") is not None:
            group_id = upsert_group(
                competition_id,
                str(round_obj["groupId"]),
                round_obj.get("groupName") or f"Grupo {round_obj['groupId']}",
            )

        round_data = normalize_round(round_obj)
        round_id = upsert_round(
            competition_id=competition_id,
            group_id=group_id,
            round_data=round_data,
        )
        print(f"  Round {round_data['label']} -> {round_id}")

        for match_raw in round_obj.get("matches", []):
            match_data = normalize_match(match_raw)

            home_team_data, home_external = normalize_team(match_raw["homeTeam"])
            away_team_data, away_external = normalize_team(match_raw["awayTeam"])

            home_team_id = upsert_team(home_team_data, home_external)
            away_team_id = upsert_team(away_team_data, away_external)

            upsert_match(
                match_data=match_data,
                competition_id=competition_id,
                round_id=round_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
            )
            total_matches += 1
            print(
                f"    {home_team_data['name']:<18} {match_data['home_score']} x "
                f"{match_data['away_score']} {away_team_data['name']:<18} [{match_data['status']}]"
            )

    print(f"Ingestão de rounds concluída: {total_matches} partidas processadas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão de dados do Brasileirão.")
    parser.add_argument("resource", choices=["standings", "rounds"])
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--group", default=None)
    args = parser.parse_args()

    try:
        if args.resource == "standings":
            ingest_standings(args.serie, group=args.group)
        else:
            ingest_rounds(args.serie, group=args.group)
    except BrasileiraoSourceError as exc:
        print(f"Erro ao consumir a fonte: [{exc.code}] {exc}", file=sys.stderr)
        sys.exit(1)
