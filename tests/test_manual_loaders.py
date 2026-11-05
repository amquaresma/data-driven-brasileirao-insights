from load_serie_c_manual import parse_first_phase, parse_games
from load_serie_c_manual import validate as validate_c
from load_serie_d_groups import parse_rows, slugify
from load_serie_d_groups import validate as validate_d_groups
from load_serie_d_matches import LINE, check_progression, normalize, winners
from load_serie_d_matches import parse as parse_d_matches


def rec(phase, leg, home, away, hg, ag, hp=None, ap=None):
    return {"phase": phase, "leg": leg, "home": home, "away": away, "hg": hg, "ag": ag, "hp": hp, "ap": ap}


def test_slugify_keeps_homonyms_apart():
    assert slugify("São Paulo") == "sao-paulo"
    assert slugify("Sampaio Corrêa") == "sampaio-correa"
    assert slugify("Sampaio Corrêa-RJ") == "sampaio-correa-rj"
    assert slugify("Ferroviária") != slugify("Ferroviário")


def test_score_line_parser():
    m = LINE.match("Cianorte 0 (5) x (4) 1 São Joseense").groupdict()
    assert (m["h"], m["hg"], m["hp"], m["ap"], m["ag"], m["a"]) == ("Cianorte", "0", "5", "4", "1", "São Joseense")
    m = LINE.match("América-RJ 1 x 1 XV de Piracicaba").groupdict()
    assert m["h"] == "América-RJ" and m["a"] == "XV de Piracicaba" and m["hp"] is None


def test_group_validation_catches_a_wrong_points_total():
    bad = [{"line": 2, "group": "A1", "team": "X", "pts": 9, "j": 10, "v": 3, "e": 1, "d": 6,
            "sg": 0, "gp": 5, "gs": 5, "gs_derived": False}]
    assert any("pontos" in e for e in validate_d_groups(bad))


def test_serie_d_group_data_is_consistent():
    rows = parse_rows()
    assert len(rows) == 96 and len({r["group"] for r in rows}) == 16
    assert validate_d_groups(rows) == []


def test_serie_d_knockout_data_is_consistent():
    recs = parse_d_matches()
    notes, errors = [], []
    normalize(recs, notes, errors)
    results = winners(recs, errors)
    check_progression(recs, results, errors)
    assert errors == []
    assert len(recs) == 128
    assert len(notes) == 4  # mandos inferidos (documentados no README)


def test_serie_c_data_is_consistent():
    first, games = parse_first_phase(), parse_games()
    errors, notes = [], []
    validate_c(first, games, errors, notes)
    assert errors == []
    assert len(first) == 20 and len(games) == 26
    assert len(notes) == 2  # dois desempates por gols pró (documentados no README)


def test_penalties_decide_a_tie_on_aggregate():
    recs = [rec("p", 1, "A", "B", 1, 1), rec("p", 2, "B", "A", 0, 0, hp=5, ap=4)]
    errors = []
    normalize(recs, [], errors)
    assert winners(recs, errors)["p"][frozenset({"A", "B"})]["winner"] == "B"
    assert errors == []


def test_unresolved_tie_is_reported_never_guessed():
    recs = [rec("p", 1, "A", "B", 1, 1), rec("p", 2, "B", "A", 0, 0)]
    errors = []
    normalize(recs, [], errors)
    winners(recs, errors)
    assert any("empatado" in e for e in errors)


def test_repeated_home_team_in_second_leg_is_flipped_keeping_goals_with_the_team():
    recs = [rec("p", 1, "A", "B", 1, 0), rec("p", 2, "A", "B", 0, 2)]
    notes, errors = [], []
    normalize(recs, notes, errors)
    assert (recs[1]["home"], recs[1]["away"], recs[1]["hg"], recs[1]["ag"]) == ("B", "A", 2, 0)
    assert len(notes) == 1
    assert winners(recs, errors)["p"][frozenset({"A", "B"})]["winner"] == "B"
