"""
Cálculos puros de rolling averages e forma recente, a partir de uma
lista de partidas já finalizadas de um time, ordenadas da mais
recente para a mais antiga.

Nenhuma função aqui toca banco de dados — recebem dados já buscados
e devolvem números. Isso facilita testar e reaproveitar a lógica.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TeamMatchResult:
    """Resultado de uma partida do ponto de vista de UM time."""

    goals_for: int
    goals_against: int

    @property
    def points(self) -> int:
        if self.goals_for > self.goals_against:
            return 3
        if self.goals_for == self.goals_against:
            return 1
        return 0

    @property
    def outcome_letter(self) -> str:
        if self.goals_for > self.goals_against:
            return "W"
        if self.goals_for == self.goals_against:
            return "D"
        return "L"


def compute_rolling_average(
    results: list[TeamMatchResult], window_size: int
) -> dict[str, float | int]:
    """
    Calcula médias de gols pró/contra/pontos considerando até
    `window_size` partidas mais recentes. Se houver menos partidas
    disponíveis que o tamanho da janela, usa todas as disponíveis
    (sem inventar dados para completar a janela).
    """
    window = results[:window_size]
    n = len(window)

    if n == 0:
        return {
            "matches_considered": 0,
            "goals_for_avg": None,
            "goals_against_avg": None,
            "points_avg": None,
        }

    goals_for_avg = sum(r.goals_for for r in window) / n
    goals_against_avg = sum(r.goals_against for r in window) / n
    points_avg = sum(r.points for r in window) / n

    return {
        "matches_considered": n,
        "goals_for_avg": round(goals_for_avg, 2),
        "goals_against_avg": round(goals_against_avg, 2),
        "points_avg": round(points_avg, 2),
    }


def compute_weighted_form_score(
    results: list[TeamMatchResult], max_matches: int = 10
) -> dict[str, object]:
    """
    Calcula uma pontuação de forma recente com peso decrescente: o
    jogo mais recente pesa mais que o mais antigo.

    Pesos lineares decrescentes (ex: para 5 jogos: 5,4,3,2,1),
    normalizados para o score ficar numa escala de 0 a 3 (mesma
    escala de "pontos médios por jogo"), facilitando comparação
    direta com points_avg.
    """
    window = results[:max_matches]
    n = len(window)

    if n == 0:
        return {"matches_considered": 0, "weighted_form_score": None, "recent_form": []}

    weights = list(range(n, 0, -1))  # [n, n-1, ..., 1]
    total_weight = sum(weights)

    weighted_sum = sum(r.points * w for r, w in zip(window, weights))
    weighted_form_score = round(weighted_sum / total_weight, 2)

    recent_form = [r.outcome_letter for r in window]

    return {
        "matches_considered": n,
        "weighted_form_score": weighted_form_score,
        "recent_form": recent_form,
    }
