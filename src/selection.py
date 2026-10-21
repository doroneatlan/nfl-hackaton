"""!
@file selection.py
@brief Sélection des actions "avec chip" et "sans chip" des TE, WR et RB.
"""

import pandas as pd

## Postes offensifs imposés par le sujet (officialPosition de players.csv).
OFFENSIVE_POSITIONS = ("TE", "WR", "RB")

## Rôle PFF d'un joueur qui part en route.
ROUTE_ROLE = "Pass Route"

## Type de bloc PFF correspondant à un chip.
CHIP_BLOCK = "CH"


def select_route_runners(pff: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Garde les TE / WR / RB partis en route, en chip ou en route directe.
    @param pff Données de scouting PFF (load_pff).
    @param players Identité des joueurs (load_players).
    @return Une ligne par joueur et par action, avec la colonne booléenne chip.
    @note Les routes précédées d'un autre type de bloc (SR, PA, BH...) sont exclues :
          elles ne sont ni un chip, ni une route directe.
    """
    runners = pff[pff["pff_role"] == ROUTE_ROLE].merge(players, on="nflId")
    runners = runners[runners["officialPosition"].isin(OFFENSIVE_POSITIONS)]

    is_chip = runners["pff_blockType"] == CHIP_BLOCK
    is_direct = runners["pff_blockType"].isna()
    runners = runners[is_chip | is_direct].copy()
    runners["chip"] = runners["pff_blockType"] == CHIP_BLOCK

    columns = ["gameId", "playId", "nflId", "displayName", "officialPosition",
               "pff_positionLinedUp", "pff_nflIdBlockedPlayer", "chip"]
    return runners[columns].reset_index(drop=True)


def add_play_context(runners: pd.DataFrame, plays: pd.DataFrame) -> pd.DataFrame:
    """!
    @brief Ajoute à chaque route le contexte de l'action (équipe, tentative, distance, couverture).
    @param runners Routes sélectionnées (select_route_runners).
    @param plays Contexte des actions (load_plays).
    @return Les routes enrichies, une ligne par joueur et par action.
    """
    context = plays[["gameId", "playId", "possessionTeam", "defensiveTeam",
                     "down", "yardsToGo", "pff_passCoverage"]]
    return runners.merge(context, on=["gameId", "playId"], how="left", validate="many_to_one")
