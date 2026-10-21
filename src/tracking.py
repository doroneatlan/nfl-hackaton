"""!
@file tracking.py
@brief Mesures tirées du tracking : profondeur de route et séparation au moment du lancer.
"""

import numpy as np
import pandas as pd

from src.loading import load_tracking, normalize_direction

## Événements marquant le snap (officiel ou détecté automatiquement).
SNAP_EVENTS = ("ball_snap", "autoevent_ballsnap")

## Événements marquant le lancer (officiel ou détecté automatiquement).
PASS_EVENTS = ("pass_forward", "autoevent_passforward")

## Valeur de la colonne team pour les lignes du ballon.
BALL_TEAM = "football"

## Clés d'une action.
PLAY_KEYS = ["gameId", "playId"]


def first_event_frame(tracking: pd.DataFrame, events: tuple, name: str) -> pd.DataFrame:
    """!
    @brief Trouve, pour chaque action, la première frame portant l'un des événements donnés.
    @param tracking Tracking d'un ou plusieurs matchs.
    @param events Noms d'événements acceptés.
    @param name Nom de la colonne de sortie.
    @return Une ligne par action trouvée : gameId, playId, name.
    @note L'événement officiel et l'automatique sont à 2 frames (0,2 s) au plus l'un de l'autre :
          on prend simplement le premier des deux.
    """
    tagged = tracking[tracking["event"].isin(events)]
    frames = tagged.groupby(PLAY_KEYS, as_index=False)["frameId"].min()
    return frames.rename(columns={"frameId": name})


def line_of_scrimmage(tracking: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Calcule la ligne de mêlée : position x du ballon au snap.
    @param tracking Tracking normalisé (normalize_direction).
    @return Une ligne par action : gameId, playId, los_x.
    """
    snap = first_event_frame(tracking, SNAP_EVENTS, "frameId")
    ball = tracking[tracking["team"] == BALL_TEAM].merge(snap, on=PLAY_KEYS + ["frameId"])
    return ball[PLAY_KEYS + ["x"]].rename(columns={"x": "los_x"})


def positions_at_pass(tracking: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Photographie de tous les joueurs au moment du lancer.
    @param tracking Tracking normalisé (normalize_direction).
    @return Une ligne par joueur et par action lancée : gameId, playId, nflId, team, x, y.
    @note Les actions sans lancer (sacks, courses du QB) n'apparaissent pas.
    """
    pass_frame = first_event_frame(tracking, PASS_EVENTS, "frameId")
    players = tracking[tracking["team"] != BALL_TEAM].merge(pass_frame, on=PLAY_KEYS + ["frameId"])
    return players[PLAY_KEYS + ["nflId", "team", "x", "y"]]


def nearest_defender_distance(snapshot: pd.DataFrame, runners: pd.DataFrame) -> pd.Series:
    """!
    @brief Distance entre chaque coureur de route et le défenseur le plus proche.
    @param snapshot Positions au lancer (positions_at_pass).
    @param runners Routes avec x, y et defensiveTeam, une ligne par joueur et par action.
    @return Distance en yards, alignée sur l'index de runners (NaN si aucun défenseur trouvé).
    """
    defenders = snapshot.rename(columns={"nflId": "defenderId", "x": "def_x", "y": "def_y"})
    pairs = runners.rename_axis("runner_row").reset_index().merge(defenders, on=PLAY_KEYS)
    pairs = pairs[pairs["team"] == pairs["defensiveTeam"]]
    pairs["distance"] = np.hypot(pairs["x"] - pairs["def_x"], pairs["y"] - pairs["def_y"])
    return pairs.groupby("runner_row")["distance"].min().reindex(runners.index)


def measure_game(game_id: int, runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Mesure profondeur et séparation au lancer pour les routes d'un match.
    @param game_id Identifiant du match.
    @param runners Routes sélectionnées avec leur contexte (add_play_context).
    @return Les routes du match ayant un lancer, avec les colonnes depth et separation (yards).
    """
    tracking = normalize_direction(load_tracking(game_id))
    snapshot = positions_at_pass(tracking)

    game_runners = runners[runners["gameId"] == game_id]
    measured = game_runners.merge(snapshot[PLAY_KEYS + ["nflId", "x", "y"]], on=PLAY_KEYS + ["nflId"])
    measured = measured.merge(line_of_scrimmage(tracking), on=PLAY_KEYS)

    measured["depth"] = measured["x"] - measured["los_x"]
    measured["separation"] = nearest_defender_distance(snapshot, measured)
    return measured.drop(columns=["x", "y", "los_x"])


def measure_all_games(runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Mesure toutes les routes, match par match, pour limiter la mémoire utilisée.
    @param runners Routes sélectionnées avec leur contexte (add_play_context).
    @return Toutes les routes mesurées.
    """
    game_ids = sorted(runners["gameId"].unique())
    return pd.concat([measure_game(game_id, runners) for game_id in game_ids], ignore_index=True)
