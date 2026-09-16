"""
Busca o detalhe (estatísticas + eventos) das partidas já finalizadas
e linkadas à Highlightly, mas que ainda não têm esse detalhe salvo.

Cada partida processada consome 1 requisição à API (plano gratuito:
100/dia). Por isso este script processa um LOTE limitado por execução
(--limit, padrão 80) em vez de tentar tudo de uma vez — rode de novo
em execuções futuras (inclusive em dias diferentes) para completar o
histórico aos poucos.

Uso:
    python ingest_highlightly_details.py a
    python ingest_highlightly_details.py a --limit 30
"""

from __future__ import annotations

import argparse
import sys

from sources.highlightly import get_match_detail, get_league_id
from sources.exceptions import BrasileiraoSourceError
from normalizers.highlightly import normalize_match_statistics, normalize_match_events
from repositories.highlightly_repo import (
    resolve_competition_id,
    load_team_id_map,
    load_matches_pending_detail,
    insert_match_statistics,
    insert_match_events,
)


def ingest_details(serie: str, season: int = 2026, limit: int = 80) -> None:
    league_id = get_league_id(serie)
    if league_id is None:
        print(f"Série '{serie}' não é coberta pela Highlightly. Nada a fazer.")
        return

    competition_id = resolve_competition_id(serie, season, league_id)
    team_id_map = load_team_id_map()

    pending = load_matches_pending_detail(competition_id)
    print(f"Partidas finalizadas sem detalhe ainda: {len(pending)}")

    batch = pending[:limit]
    print(f"Processando {len(batch)} nesta execução (limite: {limit})...")

    processed = 0
    errors = 0

    for match_id, hl_external_id in batch:
        try:
            detail = get_match_detail(int(hl_external_id))
        except BrasileiraoSourceError as exc:
            print(f"  [erro] match {match_id[:8]} (hl={hl_external_id}): {exc}")
            errors += 1
            continue

        stats = normalize_match_statistics(detail)
        events = normalize_match_events(detail)

        n_stats = insert_match_statistics(match_id, team_id_map, stats)
        n_events = insert_match_events(match_id, team_id_map, events)

        processed += 1
        print(f"  [{processed}/{len(batch)}] match {match_id[:8]}: {n_stats} stats, {n_events} eventos")

    print()
    print(f"Concluído: {processed} partidas processadas, {errors} erros.")
    remaining = len(pending) - processed
    if remaining > 0:
        print(f"Ainda restam {remaining} partidas sem detalhe. Rode novamente para continuar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão de detalhes (stats/eventos) da Highlightly.")
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    try:
        ingest_details(args.serie, args.season, args.limit)
    except BrasileiraoSourceError as exc:
        print(f"Erro ao consumir a fonte: [{exc.code}] {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        sys.exit(1)
