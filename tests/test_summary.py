"""!
@file test_summary.py
@brief Tests de la fiche de synthèse par joueur et du fichier player_summary.csv.
"""

import math

import pandas as pd
import pytest

from src.compute import RESULTS_DIR
from src.summary import (
    MIN_CHIPS,
    VERDICT_BAD,
    VERDICT_GOOD,
    VERDICT_UNKNOWN,
    VERDICT_UNSURE,
    mean_by_chip,
    verdict,
)

## Colonnes attendues par l'interface (contrat de la ROADMAP).
CONTRACT_COLUMNS = {
    "nflId", "nom", "poste", "equipe", "nb_chips", "nb_sans_chip", "nb_chips_mesures",
    "profondeur_chip", "profondeur_sans_chip", "cout_profondeur",
    "separation_chip", "separation_sans_chip",
    "pressions_attendues", "pressions_reelles",
    "pression_chip", "pression_sans_chip", "pression_evitee",
    "confiance", "fiabilite", "verdict", "explication",
}


@pytest.fixture(scope="module")
def summary() -> pd.DataFrame:
    """! @brief Fichier produit par python -m src.compute. """
    path = RESULTS_DIR / "player_summary.csv"
    if not path.exists():
        pytest.skip("Lancer d'abord : python -m src.compute")
    return pd.read_csv(path)


# --- Verdict ---


def test_verdict_good_when_confident():
    """! @brief Rentable dès 75 % de confiance que le chip réduit la pression. """
    assert verdict(MIN_CHIPS, 75.0) == VERDICT_GOOD


def test_verdict_bad_when_confident_it_hurts():
    """! @brief Pas rentable dès 75 % de confiance que le chip ne réduit pas la pression. """
    assert verdict(MIN_CHIPS, 25.0) == VERDICT_BAD


def test_verdict_unsure_in_between():
    """! @brief Entre les deux, le hasard peut tout expliquer : incertain. """
    assert verdict(MIN_CHIPS, 50.0) == VERDICT_UNSURE
    assert verdict(MIN_CHIPS, 74.0) == VERDICT_UNSURE


def test_verdict_unknown_with_few_chips():
    """! @brief Pas de jugement en dessous de MIN_CHIPS chips. """
    assert verdict(MIN_CHIPS - 1, 99.0) == VERDICT_UNKNOWN


def test_verdict_unknown_without_pressure():
    """! @brief Pas de jugement si la pression n'a pas pu être mesurée. """
    assert verdict(MIN_CHIPS, math.nan) == VERDICT_UNKNOWN


# --- Moyennes par joueur ---


def test_mean_by_chip_splits_groups():
    """! @brief Les moyennes avec et sans chip sont calculées séparément. """
    measured = pd.DataFrame({"nflId": [1, 1, 1], "chip": [True, False, False],
                             "depth": [2.0, 6.0, 8.0]})
    result = mean_by_chip(measured, "depth", "profondeur")
    assert result.loc[1, "profondeur_chip"] == 2.0
    assert result.loc[1, "profondeur_sans_chip"] == 7.0


def test_mean_by_chip_without_chips_gives_nan():
    """! @brief Un joueur sans chip a une moyenne "avec chip" vide, sans planter. """
    measured = pd.DataFrame({"nflId": [1], "chip": [False], "depth": [6.0]})
    result = mean_by_chip(measured, "depth", "profondeur")
    assert pd.isna(result.loc[1, "profondeur_chip"])


# --- Fichier produit pour l'interface ---


def test_summary_respects_contract(summary):
    """! @brief Le CSV contient toutes les colonnes promises à l'interface. """
    assert CONTRACT_COLUMNS <= set(summary.columns)


def test_summary_only_offensive_positions(summary):
    """! @brief Sujet : uniquement des TE, WR et RB. """
    assert set(summary["poste"]) <= {"TE", "WR", "RB"}


def test_summary_one_row_per_player(summary):
    """! @brief Un joueur n'apparaît qu'une fois. """
    assert summary["nflId"].is_unique


def test_summary_verdicts_are_known(summary):
    """! @brief Le verdict prend uniquement les trois valeurs prévues. """
    assert set(summary["verdict"]) <= {VERDICT_GOOD, VERDICT_BAD, VERDICT_UNSURE, VERDICT_UNKNOWN}


def test_summary_confidence_matches_verdict(summary):
    """! @brief Chaque verdict "rentable" a au moins 75 % de confiance, chaque "pas rentable" au plus 25 %. """
    assert (summary.loc[summary["verdict"] == VERDICT_GOOD, "confiance"] >= 75).all()
    assert (summary.loc[summary["verdict"] == VERDICT_BAD, "confiance"] <= 25).all()


def test_summary_every_judged_player_is_explained(summary):
    """! @brief Le coach a une phrase d'explication pour chaque joueur. """
    assert summary["explication"].str.len().gt(0).all()


def test_summary_has_judged_players(summary):
    """! @brief Assez de joueurs jugés pour que l'interface soit utile. """
    judged = summary[summary["verdict"] != VERDICT_UNKNOWN]
    assert len(judged) >= 30


def test_summary_pressures_are_percentages(summary):
    """! @brief Les pressions sont exprimées en % (entre 0 et 100). """
    pressures = summary[["pression_chip", "pression_sans_chip"]].dropna()
    assert pressures.stack().between(0, 100).all()
