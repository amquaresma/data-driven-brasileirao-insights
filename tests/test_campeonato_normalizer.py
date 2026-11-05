from normalizers.campeonato_brasileiro import (
    normalize_competition,
    normalize_groups,
    normalize_standings_entries,
    normalize_team,
)

TEAM = {"id": 262, "name": "Flamengo", "shortName": "FLA", "badge": "http://x/b.svg"}


def payload(grouped):
    return {
        "grouped": grouped,
        "tables": [
            {
                "id": 5962 if grouped else "overall",
                "name": "Grupo B" if grouped else "Classificacao geral",
                "entries": [
                    {"position": 1, "team": TEAM, "points": 6, "matches": 2, "movement": 0,
                     "recentForm": ["W", "W"], "legend": {"name": "Libertadores"}},
                    {"position": 2, "team": {**TEAM, "id": 1}, "points": 3, "legend": None},
                ],
            }
        ],
    }


def test_team_ids_become_strings():
    team, external = normalize_team(TEAM)
    assert team == {"name": "Flamengo", "short_name": "FLA", "badge_url": "http://x/b.svg"}
    assert external == {"provider": "campeonato-brasileiro-api", "external_id": "262"}


def test_ungrouped_standings_have_no_group():
    assert normalize_groups(payload(False)) == []
    assert all(e["group_external_id"] is None for e in normalize_standings_entries(payload(False)))


def test_grouped_standings_carry_the_group_id():
    assert normalize_groups(payload(True)) == [{"external_id": "5962", "name": "Grupo B"}]
    entries = normalize_standings_entries(payload(True))
    assert entries[0]["group_external_id"] == "5962"
    assert entries[0]["movement"] == "0"
    assert entries[0]["legend"] == "Libertadores"
    assert entries[1]["legend"] is None and entries[1]["movement"] is None


def test_competition_missing_fields_become_none():
    raw = {"grouped": False, "competition": {"code": "a", "season": 2026, "name": "X"}}
    c = normalize_competition(raw)
    assert (c["code"], c["season"], c["grouped"]) == ("a", 2026, False)
    assert c["phase_description"] is None and c["source_provider"] is None
