"""!
@file test_selection.py
@brief Tests de la sélection des routes avec et sans chip.
"""

import pandas as pd
import pytest

from src.loading import load_pff, load_players, load_plays
from src.selection import (
    CHIP_BLOCK,
    OFFENSIVE_POSITIONS,
    add_play_context,
    select_route_runners,
)


@pytest.fixture(scope="module")
def runners() -> pd.DataFrame:
    """! @brief Routes réelles sélectionnées, avec leur contexte. """
    selected = select_route_runners(load_pff(), load_players())
    return add_play_context(selected, load_plays())


# --- Tests sur des données construites à la main ---


def make_pff(role: str, block_type) -> pd.DataFrame:
    """!
    @brief Construit une ligne PFF minimale pour le joueur 1.
    @param role Rôle PFF du joueur.
    @param block_type Type de bloc PFF (ou None).
    @return DataFrame d'une ligne.
    """
    return pd.DataFrame({
        "gameId": [1], "playId": [1], "nflId": [1],
        "pff_role": [role], "pff_positionLinedUp": ["TE-L"],
        "pff_nflIdBlockedPlayer": [None], "pff_blockType": [block_type],
    })


def make_players(position: str) -> pd.DataFrame:
    """!
    @brief Construit la fiche du joueur 1.
    @param position Poste officiel du joueur.
    @return DataFrame d'une ligne.
    """
    return pd.DataFrame({"nflId": [1], "displayName": ["Test"], "officialPosition": [position]})


def test_chip_route_is_kept_as_chip():
    """! @brief Une route précédée d'un chip est gardée avec chip == True. """
    result = select_route_runners(make_pff("Pass Route", CHIP_BLOCK), make_players("TE"))
    assert result["chip"].tolist() == [True]


def test_direct_route_is_kept_without_chip():
    """! @brief Une route sans bloc est gardée avec chip == False. """
    result = select_route_runners(make_pff("Pass Route", None), make_players("WR"))
    assert result["chip"].tolist() == [False]


def test_other_block_types_are_excluded():
    """! @brief Une route précédée d'un autre bloc (ici SR) n'est dans aucun groupe. """
    result = select_route_runners(make_pff("Pass Route", "SR"), make_players("TE"))
    assert result.empty


def test_blockers_are_excluded():
    """! @brief Un joueur qui reste bloquer (Pass Block) n'est pas un coureur de route. """
    result = select_route_runners(make_pff("Pass Block", CHIP_BLOCK), make_players("RB"))
    assert result.empty


def test_non_offensive_positions_are_excluded():
    """! @brief Sujet : un fullback (FB) n'est pas dans les postes TE / WR / RB. """
    result = select_route_runners(make_pff("Pass Route", CHIP_BLOCK), make_players("FB"))
    assert result.empty


# --- Tests sur les vraies données ---


def test_only_offensive_positions(runners):
    """! @brief Sujet : toutes les routes sélectionnées sont des TE, WR ou RB. """
    assert set(runners["officialPosition"]) == set(OFFENSIVE_POSITIONS)


def test_each_position_has_chips(runners):
    """! @brief Chaque poste a des chips, donc chaque poste peut être analysé. """
    chips_by_position = runners[runners["chip"]].groupby("officialPosition").size()
    assert (chips_by_position > 0).all()
    assert set(chips_by_position.index) == set(OFFENSIVE_POSITIONS)


def test_enough_chips_to_analyse(runners):
    """! @brief Assez de chips pour une analyse (environ 1 450 attendus). """
    assert runners["chip"].sum() > 1000


def test_one_row_per_player_and_play(runners):
    """! @brief Un joueur n'apparaît qu'une fois par action. """
    assert not runners.duplicated(["gameId", "playId", "nflId"]).any()


def test_every_chip_targets_a_defender(runners):
    """! @brief Chaque chip indique le défenseur bousculé (utile pour la page Adversaire). """
    chips = runners[runners["chip"]]
    assert chips["pff_nflIdBlockedPlayer"].notna().all()


def test_every_route_has_play_context(runners):
    """! @brief Chaque route a son équipe et sa situation de jeu. """
    assert runners[["possessionTeam", "down", "yardsToGo"]].notna().all().all()
