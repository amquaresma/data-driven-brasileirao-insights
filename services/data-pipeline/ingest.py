"""
Orquestra a ingestão de uma série do Campeonato Brasileiro:

    fetch (sources) -> normalize (normalizers) -> persist (repositories)

Uso:
    python ingest.py a
    python ingest.py d --group A1
"""

from __future__ import annotations

import argparse
import sys

from sources.campeonato_brasileiro import get_standings, Serie
from sources.exceptions import BrasileiraoSourceError
from normalizers.campeonato_brasileiro import (
    normalize_competition,
    normalize_team,
    normalize_standings_entries,
)
from repositories.supabase_repo import (
    upsert_competition,
    upsert_team,
    upsert_standings_entry,
)


def ingest_standings(serie: Serie, *, group: str | None = None) -> None:
    print(f"Buscando standings da série '{serie}'" + (f" (grupo {group})" if group else "") + "...")

    raw = get_standings(serie, group=group)

    competition = normalize_competition(raw)
    competition_id = upsert_competition(competition)
    print(f"  Competição: {competition['name']} -> {competition_id}")

    entries = normalize_standings_entries(raw)
    print(f"  {len(entries)} entradas de classificação encontradas.")

    for entry in entries:
        team_data, external_id_data = normalize_team(entry["team"])
        team_id = upsert_team(team_data, external_id_data)

        # group_id ainda não é resolvido aqui — Etapa 4.2 seguinte
        # (grupos da Série D). Por enquanto, None para competições
        # sem grupo, que é o caso já validado (Série A).
        upsert_standings_entry(
            competition_id=competition_id,
            team_id=team_id,
            group_id=None,
            entry=entry,
        )
        print(f"    [{entry['position']:>2}] {team_data['name']:<20} {entry['points']} pts")

    print("Ingestão concluída com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão de standings do Brasileirão.")
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--group", default=None)
    args = parser.parse_args()

    try:
        ingest_standings(args.serie, group=args.group)
    except BrasileiraoSourceError as exc:
        print(f"Erro ao consumir a fonte: [{exc.code}] {exc}", file=sys.stderr)
        sys.exit(1)
