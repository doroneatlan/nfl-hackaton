"""!
@file test_loading.py
@brief Tests du chargement des données et de la normalisation du sens de jeu.
"""

import pandas as pd
import pytest

from src.loading import (
    DATA_DIR,
    FIELD_LENGTH,
    FIELD_WIDTH,
    PFF_COLUMNS,
    PLAY_COLUMNS,
    TRACKING_COLUMNS,
    load_games,
    load_pff,
    load_players,
    load_plays,
    load_tracking,
    normalize_direction,
)

## Match utilisé pour les tests sur le vrai tracking.
SAMPLE_GAME_ID = 2021090900

## Postes offensifs imposés par le sujet.
OFFENSIVE_POSITIONS = {"TE", "WR", "RB"}


@pytest.fixture(scope="module")
def plays() -> pd.DataFrame:
    """! @brief Actions chargées une seule fois pour tout le module. """
    return load_plays()


@pytest.fixture(scope="module")
def tracking() -> pd.DataFrame:
    """! @brief Tracking brut du match de test. """
    return load_tracking(SAMPLE_GAME_ID)


# --- normalize_direction : tests sur des données construites à la main ---


def make_frame(direction: str, x: float, y: float) -> pd.DataFrame:
    """!
    @brief Construit un tracking minimal d'une seule ligne.
    @param direction Sens de jeu ("left" ou "right").
    @param x Position sur la longueur du terrain.
    @param y Position sur la largeur du terrain.
    @return DataFrame d'une ligne.
    """
    return pd.DataFrame({"playDirection": [direction], "x": [x], "y": [y]})


def test_normalize_keeps_right_plays_unchanged():
    """! @brief Une action jouée vers la droite garde ses coordonnées. """
    result = normalize_direction(make_frame("right", 30.0, 10.0))
    assert result.loc[0, "x"] == 30.0
    assert result.loc[0, "y"] == 10.0


def test_normalize_flips_left_plays():
    """! @brief Une action jouée vers la gauche est retournée en x et en y. """
    result = normalize_direction(make_frame("left", 30.0, 10.0))
    assert result.loc[0, "x"] == pytest.approx(FIELD_LENGTH - 30.0)
    assert result.loc[0, "y"] == pytest.approx(FIELD_WIDTH - 10.0)


def test_normalize_does_not_modify_input():
    """! @brief La normalisation renvoie une copie sans toucher au tracking d'origine. """
    original = make_frame("left", 30.0, 10.0)
    normalize_direction(original)
    assert original.loc[0, "x"] == 30.0


# --- Chargement : les fichiers fournis sont lisibles et complets ---


def test_plays_have_expected_columns(plays):
    """! @brief plays.csv contient nos colonnes et une seule ligne par action. """
    assert set(plays.columns) == set(PLAY_COLUMNS)
    assert not plays.duplicated(["gameId", "playId"]).any()


def test_pff_has_expected_columns():
    """! @brief pffScoutingData.csv contient toutes les colonnes dont on a besoin. """
    assert set(load_pff().columns) == set(PFF_COLUMNS)


def test_every_game_has_a_tracking_file():
    """! @brief Chaque match de games.csv a son fichier de tracking, et inversement. """
    files = (DATA_DIR / "tracking").glob("tracking_*.csv")
    tracked_ids = {int(path.stem.removeprefix("tracking_")) for path in files}
    assert set(load_games()["gameId"]) == tracked_ids


def test_tracking_has_expected_columns(tracking):
    """! @brief Le tracking chargé contient uniquement les colonnes demandées. """
    assert set(tracking.columns) == set(TRACKING_COLUMNS)


def test_tracking_ball_rows_have_no_player_id(tracking):
    """! @brief Les lignes du ballon existent et n'ont pas d'identifiant joueur. """
    ball = tracking[tracking["team"] == "football"]
    assert len(ball) > 0
    assert ball["nflId"].isna().all()


# --- Conformité avec le sujet ---


def test_offensive_positions_are_present():
    """! @brief Sujet : les postes TE, WR et RB existent dans les joueurs. """
    positions = set(load_players()["officialPosition"])
    assert OFFENSIVE_POSITIONS <= positions


def test_play_direction_values(tracking):
    """! @brief Sujet : playDirection vaut uniquement "left" ou "right". """
    assert set(tracking["playDirection"]) == {"left", "right"}


def test_pass_result_values(plays):
    """! @brief Sujet : passResult ne prend que les valeurs C, I, S, IN et R. """
    expected = {"C", "I", "S", "IN", "R"}
    assert set(plays["passResult"].dropna()) <= expected


def test_normalized_positions_stay_on_field(tracking):
    """! @brief Après normalisation, les positions restent sur le terrain (marge de 10 yards). """
    result = normalize_direction(tracking)
    assert result["x"].between(-10, FIELD_LENGTH + 10).all()
    assert result["y"].between(-10, FIELD_WIDTH + 10).all()


def test_offense_moves_forward_after_normalization(tracking, plays):
    """! @brief Sujet : après normalisation, l'attaque avance vers les x croissants dans les deux sens. """
    result = normalize_direction(tracking).merge(
        plays[["gameId", "playId", "possessionTeam"]], on=["gameId", "playId"]
    )
    offense = result[result["team"] == result["possessionTeam"]]
    moves = offense.groupby(["playId", "nflId", "playDirection"])["x"].agg(["first", "last"])
    mean_gain = (moves["last"] - moves["first"]).groupby("playDirection").mean()
    assert (mean_gain > 0).all()
