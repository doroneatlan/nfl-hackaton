"""!
@file test_tracking.py
@brief Tests des mesures de tracking : ligne de mêlée, profondeur et séparation au lancer.
"""

import pandas as pd
import pytest

from src.loading import load_pff, load_players, load_plays
from src.selection import add_play_context, select_route_runners
from src.tracking import (
    first_event_frame,
    line_of_scrimmage,
    measure_game,
    nearest_defender_distance,
    positions_at_pass,
)

## Match utilisé pour les tests sur le vrai tracking.
SAMPLE_GAME_ID = 2021090900


def make_tracking(pass_event: str = "pass_forward") -> pd.DataFrame:
    """!
    @brief Construit une action jouée à la main, déjà normalisée.
    @param pass_event Événement de lancer à utiliser à la frame 2.
    @return Tracking minimal : ballon, 1 attaquant (équipe A) et 2 défenseurs (équipe B).

    Frame 1 (snap) : ballon en x = 50.
    Frame 2 (lancer) : attaquant en (58, 20), défenseurs en (60, 20) et (70, 30).
    Attendu : profondeur = 8 yards, séparation = 2 yards.
    """
    rows = [
        # nflId, frameId, team, x, y, event
        (None, 1, "football", 50.0, 25.0, "ball_snap"),
        (1, 1, "A", 50.0, 20.0, "ball_snap"),
        (2, 1, "B", 55.0, 20.0, "ball_snap"),
        (3, 1, "B", 60.0, 30.0, "ball_snap"),
        (None, 2, "football", 45.0, 25.0, pass_event),
        (1, 2, "A", 58.0, 20.0, pass_event),
        (2, 2, "B", 60.0, 20.0, pass_event),
        (3, 2, "B", 70.0, 30.0, pass_event),
    ]
    tracking = pd.DataFrame(rows, columns=["nflId", "frameId", "team", "x", "y", "event"])
    tracking["gameId"] = 1
    tracking["playId"] = 1
    return tracking


def make_runner() -> pd.DataFrame:
    """!
    @brief L'attaquant de make_tracking positionné au lancer.
    @return DataFrame d'une ligne avec x, y et l'équipe adverse.
    """
    return pd.DataFrame({"gameId": [1], "playId": [1], "nflId": [1],
                         "x": [58.0], "y": [20.0], "defensiveTeam": ["B"]})


@pytest.fixture(scope="module")
def measured() -> pd.DataFrame:
    """! @brief Routes réelles mesurées sur le match de test. """
    runners = add_play_context(select_route_runners(load_pff(), load_players()), load_plays())
    return measure_game(SAMPLE_GAME_ID, runners)


# --- Tests sur une action construite à la main ---


def test_first_event_frame_finds_pass():
    """! @brief La frame du lancer est bien la frame 2. """
    frames = first_event_frame(make_tracking(), ("pass_forward",), "pass_frame")
    assert frames["pass_frame"].tolist() == [2]


def test_first_event_frame_accepts_auto_event():
    """! @brief Sans événement officiel, l'événement automatique est utilisé. """
    tracking = make_tracking(pass_event="autoevent_passforward")
    frames = first_event_frame(tracking, ("pass_forward", "autoevent_passforward"), "pass_frame")
    assert frames["pass_frame"].tolist() == [2]


def test_line_of_scrimmage_is_ball_at_snap():
    """! @brief La ligne de mêlée est la position du ballon au snap, pas au lancer. """
    assert line_of_scrimmage(make_tracking())["los_x"].tolist() == [50.0]


def test_positions_at_pass_excludes_ball():
    """! @brief La photo au lancer contient les 3 joueurs, sans le ballon. """
    snapshot = positions_at_pass(make_tracking())
    assert sorted(snapshot["nflId"]) == [1, 2, 3]


def test_play_without_pass_is_ignored():
    """! @brief Une action sans lancer (sack) ne produit aucune photo. """
    tracking = make_tracking(pass_event="qb_sack")
    assert positions_at_pass(tracking).empty


def test_nearest_defender_distance():
    """! @brief La séparation est la distance au défenseur le plus proche (2 yards). """
    snapshot = positions_at_pass(make_tracking())
    distance = nearest_defender_distance(snapshot, make_runner())
    assert distance.tolist() == [pytest.approx(2.0)]


def test_teammates_are_not_defenders():
    """! @brief Un coéquipier collé au coureur ne compte pas comme défenseur. """
    tracking = make_tracking()
    teammate = pd.DataFrame([{"gameId": 1, "playId": 1, "nflId": 4, "frameId": 2,
                              "team": "A", "x": 58.5, "y": 20.0, "event": "pass_forward"}])
    snapshot = positions_at_pass(pd.concat([tracking, teammate], ignore_index=True))
    distance = nearest_defender_distance(snapshot, make_runner())
    assert distance.tolist() == [pytest.approx(2.0)]


# --- Tests sur les vraies données ---


def test_measures_are_present(measured):
    """! @brief Chaque route mesurée a une profondeur et une séparation. """
    assert len(measured) > 0
    assert measured[["depth", "separation"]].notna().all().all()


def test_depth_is_plausible(measured):
    """! @brief La profondeur au lancer reste dans les limites d'un terrain (en yards). """
    assert measured["depth"].between(-20, 70).all()


def test_separation_is_positive(measured):
    """! @brief Un défenseur ne peut pas être exactement sur le receveur. """
    assert (measured["separation"] > 0).all()


def test_receivers_go_downfield(measured):
    """! @brief Sujet : les WR et TE sans chip finissent en moyenne au-delà de la ligne. """
    direct = measured[~measured["chip"] & measured["officialPosition"].isin(["WR", "TE"])]
    assert direct["depth"].mean() > 0


def test_measure_keeps_selection_columns(measured):
    """! @brief La mesure garde les colonnes utiles pour la suite (chip, poste, contexte). """
    expected = {"chip", "officialPosition", "possessionTeam", "defensiveTeam", "depth", "separation"}
    assert expected <= set(measured.columns)
