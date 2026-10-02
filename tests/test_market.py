"""Tests for Transfermarkt name matching and verification on hand-built data."""
import pandas as pd

from scout.market import CLUB_STOPWORDS, best_candidate, name_score, normalise, verify


def test_normalise_accents_hyphens_case():
    assert normalise("Kylian Mbappé-Lottin") == ["kylian", "mbappe", "lottin"]
    assert normalise("Semih Kılıçsoy") == ["semih", "kilicsoy"]
    assert normalise("Martin Ødegaard") == ["martin", "odegaard"]
    assert normalise("1.FC Köln", CLUB_STOPWORDS) == ["koln"]


def test_name_score_ignores_order_extra_names_and_initials():
    assert name_score("Son Heung-Min", "Heung-min Son") == 1.0
    assert name_score("Kylian Mbappe-Lottin", "Kylian Mbappé") > 0.9
    assert name_score("V. Júnior", "Vinicius Junior") > 0.9
    assert name_score("Kylian Mbappé", "Jude Bellingham") < 0.5


def test_fuzzy_match_picks_right_teammate():
    squad = pd.Series({1: "Vinicius Junior", 2: "Vinícius Tobias", 3: "Jude Bellingham",
                       4: "Kylian Mbappé", 5: "Rodrygo"})
    assert best_candidate("Vinícius Júnior", squad)[0] == 1
    assert best_candidate("Kylian Mbappe-Lottin", squad)[0] == 4
    assert best_candidate("Rodrygo", squad)[0] == 5
    assert best_candidate("Nobody", pd.Series(dtype=str)) == (None, 0.0)


def test_verification_flags_goals_mismatch():
    matches = pd.DataFrame({"understat_player_id": [1, 2, 3], "transfermarkt_player_id": pd.array([10, 20, None], "Int64")})
    understat = pd.DataFrame({"player_id": [1, 1, 2, 3], "goals": [5, 5, 3, 1], "minutes": [90, 90, 900, 90]})
    tm = pd.DataFrame({"player_id": [10, 20], "goals": [7, 3], "minutes_played": [180, 600]})
    v = verify(matches, understat, tm).set_index("understat_player_id")
    assert v.loc[1, "flag_reason"] == "goals"           # 10 vs 7: off by 3 > 2
    assert v.loc[2, "flag_reason"] == "minutes"         # 900 vs 600: off by 33% > 20%
    assert v.loc[3, "flag_reason"] == "unmatched" and not v.loc[3, "verification_flag"]
    assert v["verification_flag"].tolist() == [True, True, False]
