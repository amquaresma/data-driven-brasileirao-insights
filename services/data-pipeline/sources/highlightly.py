"""
Wrapper Python para a Highlightly Football API.

Diferente da campeonato-brasileiro-api (que exige subprocess de CLI
JS), a Highlightly é uma API REST de verdade — chamamos via HTTP
direto com httpx.

Cobertura confirmada: ligas Série A (id 61205), Série B (id 62056) e
Série C (id 64609) do Brasileirão. A Série D NÃO está na cobertura da
Highlightly (confirmado varrendo as 108 ligas do Brasil disponíveis)
— por isso ela é tratada como ausente/opcional em todo este módulo,
nunca como erro.

Diferencial importante desta fonte: /matches retorna o calendário
COMPLETO da temporada (ex: 380 partidas para a Série A 2026), ao
contrário da campeonato-brasileiro-api que só expõe a rodada ativa.
Isso nos dá acesso a histórico real de partidas já finalizadas.

Referência: openapi.json fornecido pelo usuário (Football API
Documentation v8.2.7).
"""

from __future__ import annotations

from typing import Any

import httpx

from config import get_settings
from .exceptions import BrasileiraoSourceError

# IDs de liga confirmados manualmente via /leagues?countryCode=BR.
# Não há endpoint de busca exata por "Brasileirão" — os nomes na
# fonte são só "Serie A", "Serie B", "Serie C".
HIGHLIGHTLY_LEAGUE_IDS: dict[str, int | None] = {
    "a": 61205,
    "b": 62056,
    "c": 64609,
    "d": None,  # não coberto pela Highlightly
}

_TIMEOUT_SECONDS = 30


def _client() -> httpx.Client:
    settings = get_settings()
    return httpx.Client(
        base_url=settings.highlightly_base_url,
        headers={"x-rapidapi-key": settings.highlightly_api_key},
        timeout=_TIMEOUT_SECONDS,
    )


def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    with _client() as client:
        try:
            response = client.get(path, params=params or {})
        except httpx.RequestError as exc:
            raise BrasileiraoSourceError(
                f"Erro de rede ao chamar Highlightly {path}: {exc}"
            ) from exc

    if response.status_code >= 400:
        raise BrasileiraoSourceError(
            f"Highlightly retornou {response.status_code} em {path}: {response.text[:300]}",
            code=str(response.status_code),
        )

    return response.json()


def get_league_id(serie: str) -> int | None:
    """Retorna o league.id da Highlightly para a série, ou None se não coberta."""
    return HIGHLIGHTLY_LEAGUE_IDS.get(serie)


def get_matches(
    serie: str,
    season: int,
    *,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Retorna uma página de partidas da temporada. Use paginate_matches()
    para percorrer todas as páginas automaticamente.
    """
    league_id = get_league_id(serie)
    if league_id is None:
        raise BrasileiraoSourceError(
            f"Série '{serie}' não é coberta pela Highlightly.",
            code="LEAGUE_NOT_COVERED",
        )

    return _get(
        "/matches",
        params={"leagueId": league_id, "season": season, "limit": limit, "offset": offset},
    )


def paginate_matches(serie: str, season: int, *, page_size: int = 100):
    """Gerador que percorre todas as partidas da temporada, página por página."""
    offset = 0
    while True:
        page = get_matches(serie, season, limit=page_size, offset=offset)
        data = page.get("data", [])
        if not data:
            break
        yield from data

        total = page.get("pagination", {}).get("totalCount", 0)
        offset += page_size
        if offset >= total:
            break


def get_match_detail(highlightly_match_id: int) -> dict[str, Any]:
    """
    Retorna o detalhe completo de uma partida (eventos, estatísticas,
    predictions, etc). A fonte retorna uma lista com um único item.
    """
    result = _get(f"/matches/{highlightly_match_id}")
    if isinstance(result, list):
        if not result:
            raise BrasileiraoSourceError(
                f"Highlightly não retornou detalhe para match {highlightly_match_id}.",
                code="MATCH_NOT_FOUND",
            )
        return result[0]
    return result


def get_box_score(highlightly_match_id: int) -> list[dict[str, Any]]:
    """Retorna o box score (estatísticas por jogador) de uma partida."""
    result = _get(f"/box-score/{highlightly_match_id}")
    return result if isinstance(result, list) else result.get("data", [])
