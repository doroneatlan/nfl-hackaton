"""!
@file loading.py
@brief Chargement des fichiers de données NFL et normalisation du tracking.
"""

from pathlib import Path

import pandas as pd

## Dossier contenant les données fournies.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

## Longueur du terrain en yards, zones d'en-but comprises.
FIELD_LENGTH = 120.0

## Largeur du terrain en yards.
FIELD_WIDTH = 53.3

## Colonnes de plays.csv utiles à l'analyse.
PLAY_COLUMNS = [
    "gameId", "playId", "possessionTeam", "defensiveTeam",
    "down", "yardsToGo", "passResult", "pff_passCoverage", "pff_passCoverageType",
]

## Colonnes de pffScoutingData.csv utiles à l'analyse.
PFF_COLUMNS = [
    "gameId", "playId", "nflId", "pff_role", "pff_positionLinedUp",
    "pff_hit", "pff_hurry", "pff_sack",
    "pff_nflIdBlockedPlayer", "pff_blockType",
]

## Colonnes du tracking utiles à l'analyse.
TRACKING_COLUMNS = [
    "gameId", "playId", "nflId", "frameId",
    "team", "playDirection", "x", "y", "event",
]


def load_games() -> pd.DataFrame:
    """!
    @brief Charge la liste des matchs.
    @return Une ligne par match (clé gameId).
    """
    return pd.read_csv(DATA_DIR / "games.csv")


def load_plays() -> pd.DataFrame:
    """!
    @brief Charge le contexte de chaque action (tentative, distance, couverture).
    @return Une ligne par action (clés gameId, playId).
    """
    return pd.read_csv(DATA_DIR / "plays.csv", usecols=PLAY_COLUMNS)


def load_players() -> pd.DataFrame:
    """!
    @brief Charge l'identité des joueurs.
    @return Une ligne par joueur (clé nflId) avec son nom et son poste officiel.
    """
    columns = ["nflId", "displayName", "officialPosition"]
    return pd.read_csv(DATA_DIR / "players.csv", usecols=columns)


def load_pff() -> pd.DataFrame:
    """!
    @brief Charge les données de scouting PFF (rôle, bloc, pression).
    @return Une ligne par joueur et par action (clés gameId, playId, nflId).
    """
    return pd.read_csv(DATA_DIR / "pffScoutingData.csv", usecols=PFF_COLUMNS)


def load_tracking(game_id: int) -> pd.DataFrame:
    """!
    @brief Charge le tracking d'un match.
    @param game_id Identifiant du match.
    @return Une ligne par joueur (ou ballon) et par frame.
    @note Les lignes du ballon ont nflId vide et team == "football".
    """
    path = DATA_DIR / "tracking" / f"tracking_{game_id}.csv"
    return pd.read_csv(path, usecols=TRACKING_COLUMNS)


def normalize_direction(tracking: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Oriente toutes les actions vers la droite (x croissant = vers l'en-but adverse).
    @param tracking Tracking brut contenant les colonnes playDirection, x et y.
    @return Copie du tracking avec x et y retournés pour les actions jouées vers la gauche.
    @warning Seuls x et y sont retournés. Si les angles o ou dir sont ajoutés à
             TRACKING_COLUMNS, il faudra aussi les tourner de 180°.
    """
    result = tracking.copy()
    to_left = result["playDirection"] == "left"
    result.loc[to_left, "x"] = FIELD_LENGTH - result.loc[to_left, "x"]
    result.loc[to_left, "y"] = FIELD_WIDTH - result.loc[to_left, "y"]
    return result
