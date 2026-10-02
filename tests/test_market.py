"""Tests for Transfermarkt name matching and verification on hand-built data."""
import pandas as pd

from scout.market import CLUB_STOPWORDS, best_candidate, map_clubs, name_score, normalise, verify


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


def test_verification_marks_players_without_shared_season_unverified():
    matches = pd.DataFrame({"understat_player_id": [1], "transfermarkt_player_id": pd.array([10], "Int64")})
    understat = pd.DataFrame({"player_id": [99], "goals": [1], "minutes": [90]})   # player 1: no 2025/26 games
    tm = pd.DataFrame({"player_id": [10], "goals": [4], "minutes_played": [900]})
    v = verify(matches, understat, tm).iloc[0]
    assert not v["verification_flag"] and v["flag_reason"].startswith("no 2025/26")


def tm_clubs(rows):
    return pd.DataFrame([{"competition_id": "FR1", "club_id": i, "name": n, "variants": [n], "in_league": lg}
                         for i, n, lg in rows])


def test_club_mapping_keeps_established_teams_on_league_clubs():
    teams = pd.DataFrame({"league": "Ligue_1", "team": ["Nice", "Troyes", "Le Mans"], "season": [2025, 2026, 2026]})
    tm = tm_clubs([(417, "OGC Nice", True), (1095, "ESTAC Troyes", False),
                   (9999, "Nice Côte d'Azur Amateurs", False), (1416, "Amiens SC", False)])
    m = map_clubs(teams, tm).set_index("understat_team")
    assert m.loc["Nice", "transfermarkt_club_id"] == 417          # never the cup side
    assert m.loc["Troyes", "transfermarkt_club_id"] == 1095       # promoted, found among the rest
    assert pd.isna(m.loc["Le Mans", "transfermarkt_club_id"])     # not in snapshot: left unmapped
