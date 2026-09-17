"""
Persistência específica da ingestão Highlightly: resolve identidades
(competição, times, partida) contra o que já existe no banco, criando
apenas o que realmente não existe ainda — nunca sobrescreve dados já
gravados por outra fonte.

Otimizado para carregar reconciliações em lote (poucas queries totais)
em vez de uma consulta por partida, já que a ingestão processa a
temporada inteira (centenas de partidas) de uma vez.
"""

from __future__ import annotations

from typing import Any

from infrastructure.supabase import get_supabase_client

PROVIDER = "highlightly"


def resolve_competition_id(code: str, season: int, highlightly_league_id: int) -> str:
    client = get_supabase_client()

    result = (
        client.table("competitions")
        .select("id")
        .eq("code", code)
        .eq("season", season)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError(
            f"Competição (code={code}, season={season}) não existe ainda. "
            "Rode a ingestão da campeonato-brasileiro-api primeiro."
        )

    competition_id = result.data[0]["id"]

    client.table("competition_external_ids").upsert(
        {
            "competition_id": competition_id,
            "provider": PROVIDER,
            "external_id": str(highlightly_league_id),
        },
        on_conflict="provider,external_id",
    ).execute()

    return competition_id


def load_team_id_map() -> dict[str, str]:
    """Carrega TODAS as reconciliações de time da Highlightly de uma vez."""
    client = get_supabase_client()
    result = (
        client.table("team_external_ids")
        .select("external_id, team_id")
        .eq("provider", PROVIDER)
        .execute()
    )
    return {row["external_id"]: row["team_id"] for row in result.data}


def load_existing_matches(competition_id: str) -> dict[tuple[str, str], list[str]]:
    """
    Carrega todas as partidas já existentes na competição, indexadas
    por (home_team_id, away_team_id). Uma lista por chave, pois turno
    e returno podem gerar mais de uma partida com o mesmo par.
    """
    client = get_supabase_client()
    result = (
        client.table("matches")
        .select("id, home_team_id, away_team_id")
        .eq("competition_id", competition_id)
        .execute()
    )
    index: dict[tuple[str, str], list[str]] = {}
    for row in result.data:
        key = (row["home_team_id"], row["away_team_id"])
        index.setdefault(key, []).append(row["id"])
    return index


def load_round_id_map(competition_id: str) -> dict[int, str]:
    """Carrega rodadas já existentes (sem grupo) na competição, por número."""
    client = get_supabase_client()
    result = (
        client.table("rounds")
        .select("id, number")
        .eq("competition_id", competition_id)
        .is_("group_id", "null")
        .execute()
    )
    return {row["number"]: row["id"] for row in result.data if row["number"] is not None}


def create_round(
    *, competition_id: str, group_id: str | None, round_data: dict[str, Any]
) -> str:
    client = get_supabase_client()
    insert_result = (
        client.table("rounds")
        .insert(
            {
                "competition_id": competition_id,
                "group_id": group_id,
                "external_id": round_data.get("external_id"),
                "number": round_data["number"],
                "total": round_data.get("total"),
                "label": round_data.get("label"),
            }
        )
        .execute()
    )
    return insert_result.data[0]["id"]


def link_match(match_id: str, highlightly_external_id: str) -> None:
    client = get_supabase_client()
    client.table("match_external_ids").upsert(
        {
            "match_id": match_id,
            "provider": PROVIDER,
            "external_id": highlightly_external_id,
        },
        on_conflict="provider,external_id",
    ).execute()


def create_match(
    *,
    match_data: dict[str, Any],
    competition_id: str,
    round_id: str | None,
    home_team_id: str,
    away_team_id: str,
) -> str:
    client = get_supabase_client()
    payload = {
        **match_data,
        "competition_id": competition_id,
        "round_id": round_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
    }
    result = (
        client.table("matches")
        .upsert(payload, on_conflict="provider,external_id")
        .execute()
    )
    return result.data[0]["id"]


def load_matches_pending_detail(competition_id: str) -> list[tuple[str, str]]:
    """
    Retorna [(match_id, highlightly_external_id)] para partidas
    finalizadas que já têm link com a Highlightly mas AINDA NÃO têm
    estatísticas salvas (usa a presença de match_statistics como
    marcador de "detalhe já processado" para não buscar de novo).
    """
    client = get_supabase_client()

    matches = (
        client.table("matches")
        .select("id, status")
        .eq("competition_id", competition_id)
        .ilike("status", "%Finished%")
        .execute()
    )
    finished_ids = {m["id"] for m in matches.data}
    if not finished_ids:
        return []

    links = (
        client.table("match_external_ids")
        .select("match_id, external_id")
        .eq("provider", PROVIDER)
        .in_("match_id", list(finished_ids))
        .execute()
    )
    match_to_external = {row["match_id"]: row["external_id"] for row in links.data}

    # PostgREST limita a 1000 linhas por resposta por padrão. Como
    # match_statistics cresce ~50-80 linhas por partida, uma única
    # chamada .execute() trunca silenciosamente para tabelas grandes,
    # fazendo esta checagem subestimar quais partidas já foram
    # processadas (e desperdiçar chamadas à API re-buscando detalhe
    # de partidas que já tinham stats). Paginamos explicitamente até
    # esgotar os resultados.
    match_ids_to_check = list(match_to_external.keys())
    already_done: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        page = (
            client.table("match_statistics")
            .select("match_id")
            .in_("match_id", match_ids_to_check)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not page.data:
            break
        already_done.update(row["match_id"] for row in page.data)
        if len(page.data) < page_size:
            break
        offset += page_size

    return [
        (match_id, external_id)
        for match_id, external_id in match_to_external.items()
        if match_id not in already_done
    ]


def insert_match_statistics(
    match_id: str, team_id_map: dict[str, str], stats: list[dict[str, Any]]
) -> int:
    client = get_supabase_client()
    rows = []
    for stat in stats:
        team_id = team_id_map.get(str(stat["highlightly_team_id"]))
        if team_id is None:
            continue
        rows.append(
            {
                "match_id": match_id,
                "team_id": team_id,
                "stat_name": stat["stat_name"],
                "stat_value": stat["stat_value"],
            }
        )
    if rows:
        client.table("match_statistics").upsert(
            rows, on_conflict="match_id,team_id,stat_name"
        ).execute()
    return len(rows)


def insert_match_events(
    match_id: str, team_id_map: dict[str, str], events: list[dict[str, Any]]
) -> int:
    client = get_supabase_client()
    rows = []
    for event in events:
        team_id = None
        if event.get("highlightly_team_id") is not None:
            team_id = team_id_map.get(str(event["highlightly_team_id"]))
        rows.append(
            {
                "match_id": match_id,
                "team_id": team_id,
                "minute": event["minute"],
                "event_type": event["event_type"],
                "player_name": event["player_name"],
                "player_external_id": event["player_external_id"],
                "assisting_player_name": event["assisting_player_name"],
                "assisting_player_external_id": event["assisting_player_external_id"],
                "substituted_player_name": event["substituted_player_name"],
            }
        )
    if rows:
        client.table("match_events").insert(rows).execute()
    return len(rows)


def resolve_or_create_player(highlightly_player_id: int, name: str, full_name: str | None, position: str | None) -> str:
    """
    Busca o player_id interno pelo external_id da Highlightly. Cria o
    jogador (e seu external_id) se ainda não existir.
    """
    client = get_supabase_client()

    existing = (
        client.table("player_external_ids")
        .select("player_id")
        .eq("provider", PROVIDER)
        .eq("external_id", str(highlightly_player_id))
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["player_id"]

    player_result = (
        client.table("players")
        .insert({"name": name, "full_name": full_name, "position": position})
        .execute()
    )
    player_id = player_result.data[0]["id"]

    client.table("player_external_ids").insert(
        {"player_id": player_id, "provider": PROVIDER, "external_id": str(highlightly_player_id)}
    ).execute()

    return player_id


def insert_player_match_statistics(
    match_id: str, team_id_map: dict[str, str], rows: list[dict[str, Any]]
) -> int:
    client = get_supabase_client()
    payloads = []

    for row in rows:
        team_id = team_id_map.get(str(row["highlightly_team_id"]))
        if team_id is None:
            continue

        player_id = resolve_or_create_player(
            row["highlightly_player_id"], row["player_name"], row["player_full_name"], row["position"]
        )

        payload = {k: v for k, v in row.items() if not k.startswith("highlightly_") and k not in ("player_name", "player_full_name")}
        payload["match_id"] = match_id
        payload["player_id"] = player_id
        payload["team_id"] = team_id
        payloads.append(payload)

    if payloads:
        client.table("player_match_statistics").upsert(
            payloads, on_conflict="match_id,player_id"
        ).execute()

    return len(payloads)
