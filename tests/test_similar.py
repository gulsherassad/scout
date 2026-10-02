"""Tests for player-name matching in the similar-players search."""
import pandas as pd

from scout.similar import find_players, normalise

NAMES = pd.Series({1: "Kylian Mbappé", 2: "Ferrán Torres", 3: "Pau Torres",
                   4: "Raul García", 5: "Raul", 6: "Jean-Philippe Mateta"})


def test_normalise_strips_accents_case_and_hyphens():
    assert normalise("  Jean-Philippe MATÉTA ") == "jean philippe mateta"


def test_accents_optional():
    assert find_players("Mbappe", NAMES) == [1]
    assert find_players("ferran torres", NAMES) == [2]


def test_several_matches_are_all_returned():
    assert sorted(find_players("Torres", NAMES)) == [2, 3]


def test_exact_full_name_wins_over_partial_matches():
    assert find_players("raul", NAMES) == [5]


def test_hyphenated_names_match_by_part():
    assert find_players("Mateta", NAMES) == [6]
    assert find_players("jean philippe", NAMES) == [6]


def test_close_misspelling_matches_and_nonsense_does_not():
    assert find_players("Mbape", NAMES) == [1]
    assert find_players("Zzzzz", NAMES) == []
