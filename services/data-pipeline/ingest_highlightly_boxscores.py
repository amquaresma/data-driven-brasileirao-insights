"""
Ingestão em massa do box score (estatísticas por jogador, com xG/xA)
das partidas finalizadas já linkadas à Highlightly.

Cada partida consome 1 requisição (plano gratuito: 100/dia), por isso
o lote é limitado por execução e o script é retomável: só processa
partidas que ainda não têm linhas em player_match_statistics.

Uso:
    python ingest_highlightly_boxscores.py a --limit 80
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from infrastructure.supabase import get_supabase_client
from sources.highlightly import get_box_score, get_league_id
from sources.exceptions import BrasileiraoSourceError
from normalizers.highlightly import normalize_player_box_score
from repositories.highlightly_repo import (
    resolve_competition_id,
    load_team_id_map,
    insert_player_match_statistics,
)

CACHE_DIR = Path(__file__).parent / ".cache"
PROVIDER = "highlightly"
PAGE = 1000


def _paginate(query_factory):
    """Percorre todas as páginas (PostgREST limita a 1000 linhas por resposta)."""
    offset = 0
    while True:
        page = query_factory().range(offset, offset + PAGE - 1).execute().data
        if not page:
            return
        yield from page
        if len(page) < PAGE:
            return
        offset += PAGE


def load_player_cache() -> dict[str, str]:
    client = get_supabase_client()
    rows = _paginate(
        lambda: client.table("player_external_ids")
        .select("external_id, player_id")
        .eq("provider", PROVIDER)
    )
    return {r["external_id"]: r["player_id"] for r in rows}


def load_pending(competition_id: str) -> list[tuple[str, str]]:
    """[(match_id, highlightly_external_id)] finalizadas, sem box score ainda."""
    client = get_supabase_client()

    finished = [
        m["id"]
        for m in _paginate(
            lambda: client.table("matches")
            .select("id")
            .eq("competition_id", competition_id)
            .ilike("status", "%Finished%")
        )
    ]
    if not finished:
        return []

    links = {
        r["match_id"]: r["external_id"]
        for r in _paginate(
            lambda: client.table("match_external_ids")
            .select("match_id, external_id")
            .eq("provider", PROVIDER)
            .in_("match_id", finished)
        )
    }

    done = {
        r["match_id"]
        for r in _paginate(
            lambda: client.table("player_match_statistics")
            .select("match_id")
            .in_("match_id", list(links.keys()))
        )
    }

    return [(mid, ext) for mid, ext in links.items() if mid not in done]


def ingest_boxscores(serie: str, season: int, limit: int) -> None:
    league_id = get_league_id(serie)
    if league_id is None:
        print(f"Série '{serie}' não é coberta pela Highlightly.")
        return

    CACHE_DIR.mkdir(exist_ok=True)
    competition_id = resolve_competition_id(serie, season, league_id)
    team_id_map = load_team_id_map()
    player_cache = load_player_cache()

    pending = load_pending(competition_id)

    # Partidas cujo box score a fonte devolveu vazio ([]) não têm dado
    # pra gravar. Pulamos para não ocuparem vaga no lote todo dia.
    # (Para tentar de novo, apague o arquivo correspondente em .cache/.)
    def _empty_in_source(hl_id: str) -> bool:
        f = CACHE_DIR / f"box_score_{hl_id}.json"
        return f.exists() and f.read_text().strip() == "[]"

    skipped_empty = [p for p in pending if _empty_in_source(p[1])]
    pending = [p for p in pending if not _empty_in_source(p[1])]
    if skipped_empty:
        print(f"Partidas sem box score na fonte (puladas): {len(skipped_empty)}")

    batch = pending[:limit]
    print(f"Partidas sem box score: {len(pending)} | nesta execução: {len(batch)}")

    done = 0
    for match_id, hl_id in batch:
        cache_file = CACHE_DIR / f"box_score_{hl_id}.json"

        if cache_file.exists():
            box = json.loads(cache_file.read_text())
        else:
            try:
                box = get_box_score(int(hl_id))
            except BrasileiraoSourceError as exc:
                if exc.code == "429":
                    print("Limite diário atingido (429). Parando; rode de novo amanhã.")
                    break
                print(f"  [erro] hl={hl_id}: {exc}")
                continue
            cache_file.write_text(json.dumps(box, ensure_ascii=False))

        rows = normalize_player_box_score(box)
        n = insert_player_match_statistics(match_id, team_id_map, rows, player_cache)
        done += 1
        print(f"  [{done}/{len(batch)}] match {match_id[:8]}: {n} jogadores")

    print(f"\nConcluído: {done} partidas. Restam {len(pending) - done}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestão de box score da Highlightly.")
    parser.add_argument("serie", choices=["a", "b", "c", "d"])
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    ingest_boxscores(args.serie, args.season, args.limit)
