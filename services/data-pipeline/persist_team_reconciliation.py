"""
Persiste team_external_ids (provider='highlightly') combinando:

1. Matches automáticos por nome normalizado (alta confiança).
2. Overrides manuais, revisados e confirmados por humano — cada
   entrada aqui documenta explicitamente qual par foi confirmado e
   por quê, em vez de decidir isso silenciosamente por heurística.

Rodar reconcile_teams_highlightly.py primeiro para qualquer série
nova, adicionar os pares confirmados em MANUAL_OVERRIDES, e só então
rodar este script.

Uso:
    python persist_team_reconciliation.py a
"""

from __future__ import annotations

import sys

from sources.highlightly import paginate_matches
from infrastructure.supabase import get_supabase_client
from reconcile_teams_highlightly import normalize, get_highlightly_teams, get_our_teams

# Pares confirmados manualmente por revisão humana (não automáticos).
# Chave: highlightly_team_id -> nosso team_id (UUID).
MANUAL_OVERRIDES: dict[int, str] = {
    # Série A
    114818: "c965fdab-a455-44c0-afd6-8e59740ef63d",   # Athletico Paranaense -> Athletico-PR
    108010: "a8b4ba5a-2070-4d28-93be-5ddddd108642",   # São Paulo FC -> São Paulo
    113967: "c681cfce-a20b-4a59-9b9f-424f8d3b7a5b",   # Vasco DA Gama -> Vasco
    676478: "11735b4c-a4d4-4877-aa85-25003ce014ab",   # RB Bragantino -> Bragantino
    # Série B
    123328: "eb819e54-7db2-447e-acbc-31494abeb37b",   # Atlético Goianiense -> Atlético-GO
    105457: "4a4c124a-09c0-4fea-af59-de30f4e316c2",   # Sport Recife -> Sport
    107159: "1875ae34-7940-49eb-9ca4-81192d48fad8",   # América Mineiro -> América-MG
    643289: "15312cad-53eb-4751-9a4a-1a1913da92dd",   # Nautico Recife -> Náutico
    # Série C
    641587: "1057b3c6-01b7-4f3b-9dc4-a935ab63ad9f",   # Santa Cruz FC -> Santa Cruz
    127583: "4ab33527-0c3a-4810-994f-46d37fb2ba4c",   # Paysandu SC -> Paysandu
}

PROVIDER = "highlightly"


def persist_reconciliation(serie: str) -> None:
    highlightly_teams = get_highlightly_teams(serie)
    our_teams = get_our_teams()
    our_by_normalized = {normalize(t["name"]): t for t in our_teams}

    client = get_supabase_client()

    persisted = 0
    skipped = []
    created = []

    for hl_id, hl_name in highlightly_teams.items():
        our_team_id = None

        norm = normalize(hl_name)
        if norm in our_by_normalized:
            our_team_id = our_by_normalized[norm]["id"]
        elif hl_id in MANUAL_OVERRIDES:
            our_team_id = MANUAL_OVERRIDES[hl_id]

        if our_team_id is None:
            # Time genuinamente novo (não existe em nenhuma fonte
            # anterior) — cria em vez de pular, já que não há
            # ambiguidade: é um time que só a Highlightly nos deu.
            new_team = (
                client.table("teams")
                .insert({"name": hl_name})
                .execute()
            )
            our_team_id = new_team.data[0]["id"]
            created.append((hl_id, hl_name, our_team_id))

        client.table("team_external_ids").upsert(
            {
                "team_id": our_team_id,
                "provider": PROVIDER,
                "external_id": str(hl_id),
            },
            on_conflict="provider,external_id",
        ).execute()
        persisted += 1

    print(f"Série {serie.upper()}: {persisted} reconciliações persistidas.")
    if created:
        print(f"  {len(created)} times novos criados (não existiam em nenhuma fonte anterior):")
        for hl_id, hl_name, team_id in created:
            print(f"    '{hl_name}' -> {team_id}")
    if skipped:
        print(f"  {len(skipped)} times SEM reconciliação (não persistidos):")
        for hl_id, hl_name in skipped:
            print(f"    Highlightly[{hl_id}] '{hl_name}' -- adicione a MANUAL_OVERRIDES se for válido")


if __name__ == "__main__":
    serie = sys.argv[1] if len(sys.argv) > 1 else "a"
    persist_reconciliation(serie)
