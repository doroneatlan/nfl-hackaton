"""!
@file test_pressure.py
@brief Tests de la pression évitée, mesurée sur le défenseur bousculé.
"""

import pandas as pd
import pytest

from src.loading import load_pff, load_players
from src.pressure import MIN_BASELINE_RUSHES, chip_pressure, rusher_pressure
from src.selection import select_route_runners

## Identifiant du défenseur fictif.
RUSHER = 99

## Identifiant du coureur fictif qui fait le chip.
RUNNER = 1


def make_pff(nb_rushes: int, pressures: int) -> pd.DataFrame:
    """!
    @brief Construit les rushs d'un défenseur fictif sur plusieurs actions.
    @param nb_rushes Nombre d'actions où il rush.
    @param pressures Nombre de ces actions (les premières) avec un hurry.
    @return Données PFF minimales, une ligne par rush.

    L'action 1 est celle où il reçoit le chip.
    """
    return pd.DataFrame({
        "gameId": 1,
        "playId": range(1, nb_rushes + 1),
        "nflId": RUSHER,
        "pff_role": "Pass Rush",
        "pff_hit": 0,
        "pff_hurry": [1 if i < pressures else 0 for i in range(nb_rushes)],
        "pff_sack": 0,
    })


def make_chip() -> pd.DataFrame:
    """!
    @brief Un chip du coureur fictif sur le défenseur fictif, à l'action 1.
    @return Routes minimales d'une ligne.
    """
    return pd.DataFrame({"gameId": [1], "playId": [1], "nflId": [RUNNER],
                         "pff_nflIdBlockedPlayer": [RUSHER], "chip": [True]})


@pytest.fixture(scope="module")
def real_chips() -> pd.DataFrame:
    """! @brief Chips réels avec leur pression. """
    pff = load_pff()
    return chip_pressure(select_route_runners(pff, load_players()), pff)


# --- Tests sur des données construites à la main ---


def test_any_pressure_column_counts():
    """! @brief Un hit, un hurry ou un sack comptent chacun comme une pression. """
    pff = make_pff(nb_rushes=3, pressures=0)
    pff.loc[0, "pff_hit"] = 1
    pff.loc[1, "pff_sack"] = 1
    assert rusher_pressure(pff)["pressure"].tolist() == [True, True, False]


def test_non_rushers_are_ignored():
    """! @brief Un défenseur en couverture n'est pas un rush. """
    pff = make_pff(nb_rushes=2, pressures=0)
    pff.loc[0, "pff_role"] = "Coverage"
    assert len(rusher_pressure(pff)) == 1


def test_baseline_excludes_the_chipped_rush():
    """!
    @brief La pression attendue se calcule sans l'action où il est bousculé.

    21 rushs, pression sur l'action 1 (le chip) et 5 autres : attendu = 5 / 20.
    """
    pff = make_pff(nb_rushes=MIN_BASELINE_RUSHES + 1, pressures=6)
    result = chip_pressure(make_chip(), pff)
    assert result["pressure"].tolist() == [True]
    assert result["expected_pressure"].tolist() == [pytest.approx(5 / 20)]


def test_rusher_with_too_few_rushes_is_ignored():
    """! @brief Sans assez de rushs, la pression habituelle n'est pas fiable : chip écarté. """
    pff = make_pff(nb_rushes=MIN_BASELINE_RUSHES, pressures=0)
    assert chip_pressure(make_chip(), pff).empty


# --- Tests sur les vraies données ---


def test_most_chips_are_measured(real_chips):
    """! @brief La grande majorité des ~1 450 chips a une pression mesurable. """
    assert len(real_chips) > 1200


def test_expected_pressure_is_a_rate(real_chips):
    """! @brief La pression attendue est un taux entre 0 et 1. """
    assert real_chips["expected_pressure"].between(0, 1).all()


def test_one_measure_per_chip(real_chips):
    """! @brief Un chip donne une seule mesure. """
    assert not real_chips.duplicated(["gameId", "playId", "nflId"]).any()
