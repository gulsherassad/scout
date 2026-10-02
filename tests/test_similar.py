"""Tests for player-name matching in the similar-players search."""
import pandas as pd

from scout.similar import apply_filters, exclude_inactive, find_players, normalise

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


def ranked_players():
    """Already in similarity order: 1 is the most similar."""
    return pd.DataFrame({
        "player": ["A", "B", "C", "D", "E"],
        "age": pd.array([22, 25, 24, None, 19], "Int64"),
        "value_m": [30.0, 10.0, 45.0, 5.0, None],
        "contract_end": pd.to_datetime(["2027-06-30", "2026-06-30", "2028-06-30", None, "2029-06-30"]),
        "similarity": [0.9, 0.8, 0.7, 0.6, 0.5],
    }, index=[1, 2, 3, 4, 5])


def test_no_filters_keeps_everyone_in_order():
    kept, removed = apply_filters(ranked_players())
    assert list(kept["player"]) == ["A", "B", "C", "D", "E"] and removed == 0


def test_each_filter():
    r = ranked_players()
    assert list(apply_filters(r, max_age=24)[0]["player"]) == ["A", "C", "E"]   # 24 itself allowed
    assert list(apply_filters(r, max_value=30)[0]["player"]) == ["A", "B", "D"]  # 30 itself allowed
    assert list(apply_filters(r, contract_before=2028)[0]["player"]) == ["A", "B"]


def test_filters_combine_keep_similarity_order_and_count_removed():
    kept, removed = apply_filters(ranked_players(), max_age=24, max_value=40, contract_before=2028)
    assert list(kept["player"]) == ["A"]
    assert removed == 4


def test_missing_field_is_removed_only_when_filtered_on():
    r = ranked_players()
    assert "D" not in set(apply_filters(r, max_age=30)[0]["player"])            # unknown age
    assert "D" in set(apply_filters(r, max_value=30)[0]["player"])              # value known


def test_exclude_inactive_keeps_order_and_counts():
    r = ranked_players().assign(active=[True, False, True, None, True])
    kept, excluded = exclude_inactive(r)
    assert list(kept["player"]) == ["A", "C", "E"] and excluded == 2
