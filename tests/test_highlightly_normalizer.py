from normalizers.highlightly import normalize_match, parse_round_number, parse_score


def test_parse_score():
    assert parse_score("3 - 1") == (3, 1)
    assert parse_score(None) == (None, None)
    assert parse_score("") == (None, None)
    assert parse_score("abc") == (None, None)
    assert parse_score("1 - 2 - 3") == (None, None)


def test_parse_round_number():
    assert parse_round_number("Regular Season - 4") == 4
    assert parse_round_number("Second Stage - 6") == 6
    assert parse_round_number("Final") is None


def hl(description, current, penalties=None):
    return {
        "id": 123,
        "date": "2026-11-05T22:30:00.000Z",
        "state": {"description": description, "score": {"current": current, "penalties": penalties}},
    }


def test_normalize_finished_match():
    n = normalize_match(hl("Finished", "2 - 1"))
    assert n["external_id"] == "123" and n["provider"] == "highlightly"
    assert (n["match_date"], n["match_time"]) == ("2026-11-05", "22:30")
    assert n["started"] is True and n["status"] == "Finished"
    assert (n["home_score"], n["away_score"]) == (2, 1)
    assert (n["penalties_home"], n["penalties_away"]) == (None, None)


def test_normalize_not_started_has_no_score():
    n = normalize_match(hl("Not started", None))
    assert n["started"] is False
    assert (n["home_score"], n["away_score"]) == (None, None)


def test_normalize_penalties():
    n = normalize_match(hl("Finished after penalties", "1 - 1", "5 - 4"))
    assert (n["penalties_home"], n["penalties_away"]) == (5, 4)
