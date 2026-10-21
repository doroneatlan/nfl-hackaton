"""!
@file pressure.py
@brief Pression évitée par un chip, mesurée au niveau du défenseur bousculé.

Comparer la pression des actions avec et sans chip est biaisé : le coach demande un chip
justement face aux meilleurs défenseurs. On compare donc chaque défenseur bousculé
à lui-même : sa pression quand il reçoit un chip, contre sa pression habituelle sans chip.
"""

import pandas as pd

## Colonnes PFF indiquant une pression sur le QB (hit, hurry ou sack).
PRESSURE_COLUMNS = ["pff_hit", "pff_hurry", "pff_sack"]

## Rôle PFF d'un défenseur qui fonce sur le QB.
RUSH_ROLE = "Pass Rush"

## Nombre minimal de rushs sans chip pour connaître la pression habituelle d'un défenseur.
MIN_BASELINE_RUSHES = 20

## Clés d'un rush : une action et un défenseur.
RUSH_KEYS = ["gameId", "playId", "rusherId"]


def rusher_pressure(pff: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Indique, pour chaque rush, si le défenseur a mis la pression sur le QB.
    @param pff Données de scouting PFF (load_pff).
    @return Une ligne par défenseur et par action : gameId, playId, rusherId, pressure.
    """
    rushes = pff[pff["pff_role"] == RUSH_ROLE].copy()
    rushes["pressure"] = rushes[PRESSURE_COLUMNS].eq(1).any(axis=1)
    return rushes.rename(columns={"nflId": "rusherId"})[RUSH_KEYS + ["pressure"]]


def chip_targets(runners: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Liste les chips avec le défenseur bousculé.
    @param runners Routes sélectionnées (select_route_runners).
    @return Une ligne par chip : gameId, playId, nflId (coureur), rusherId.
    """
    chips = runners[runners["chip"]]
    chips = chips.rename(columns={"pff_nflIdBlockedPlayer": "rusherId"})
    return chips[["gameId", "playId", "nflId", "rusherId"]]


def rusher_baseline(rushes: pd.DataFrame, chips: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Pression habituelle de chaque défenseur, sur ses rushs sans chip.
    @param rushes Rushs avec pression (rusher_pressure).
    @param chips Chips avec défenseur bousculé (chip_targets).
    @return Une ligne par défenseur ayant assez de rushs : rusherId, expected_pressure.
    """
    chipped = chips[RUSH_KEYS].drop_duplicates().assign(chipped=True)
    rushes = rushes.merge(chipped, on=RUSH_KEYS, how="left")
    unchipped = rushes[rushes["chipped"].isna()]

    baseline = unchipped.groupby("rusherId")["pressure"].agg(["mean", "size"])
    baseline = baseline[baseline["size"] >= MIN_BASELINE_RUSHES]
    return baseline.rename(columns={"mean": "expected_pressure"})[["expected_pressure"]].reset_index()


def chip_pressure(runners: pd.DataFrame, pff: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Pression réelle et pression attendue du défenseur bousculé, pour chaque chip.
    @param runners Routes sélectionnées (select_route_runners).
    @param pff Données de scouting PFF (load_pff).
    @return Une ligne par chip mesurable : gameId, playId, nflId, rusherId, pressure, expected_pressure.
    @note Un chip est écarté si le défenseur ne rush pas sur l'action
          ou s'il a moins de MIN_BASELINE_RUSHES rushs sans chip.
    """
    rushes = rusher_pressure(pff)
    chips = chip_targets(runners)
    measured = chips.merge(rushes, on=RUSH_KEYS)
    return measured.merge(rusher_baseline(rushes, chips), on="rusherId")
