"""!
@file test_outputs.py
@brief Tests des fichiers rushers.csv, situations.csv et routes.csv, et du côté des défenseurs.
"""

import pandas as pd
import pytest

from src.compute import RESULTS_DIR
from src.rushers import offense_side


def read_result(name: str) -> pd.DataFrame:
    """!
    @brief Lit un fichier de results/, ou saute le test s'il n'a pas été généré.
    @param name Nom du fichier CSV.
    @return Le contenu du fichier.
    """
    path = RESULTS_DIR / name
    if not path.exists():
        pytest.skip("Lancer d'abord : python -m src.compute")
    return pd.read_csv(path)


# --- Côté des défenseurs ---


def test_left_defender_is_on_offense_right():
    """! @brief Vérifié sur le tracking : un défenseur "L" est à droite de l'attaque. """
    assert offense_side("LE") == "droite"
    assert offense_side("LOLB") == "droite"
    assert offense_side("DLT") == "droite"


def test_right_defender_is_on_offense_left():
    """! @brief Un défenseur "R" est à gauche de l'attaque. """
    assert offense_side("REO") == "gauche"
    assert offense_side("DRT") == "gauche"


def test_nose_tackle_is_center():
    """! @brief Le nose tackle est au centre. """
    assert offense_side("NT") == "centre"


# --- rushers.csv ---


def test_rushers_are_unique_and_ranked():
    """! @brief Un défenseur par ligne, du plus dangereux au moins dangereux. """
    rushers = read_result("rushers.csv")
    assert rushers["nflId"].is_unique
    assert rushers["nb_pressions"].is_monotonic_decreasing


def test_rushers_are_defenders():
    """! @brief Aucun TE / WR / RB / QB dans les défenseurs. """
    rushers = read_result("rushers.csv")
    assert not set(rushers["poste"]) & {"TE", "WR", "RB", "QB"}


def test_rushers_rates_are_percentages():
    """! @brief Les taux de pression sont entre 0 et 100. """
    rushers = read_result("rushers.csv")
    assert rushers["taux_pression"].between(0, 100).all()


# --- situations.csv ---


def test_situations_cover_three_dimensions():
    """! @brief Distance, tentative et couverture sont toutes présentes. """
    situations = read_result("situations.csv")
    assert set(situations["situation"]) == {"distance", "tentative", "couverture"}


def test_situations_show_a_depth_cost():
    """! @brief Dans chaque situation, le chip coûte de la profondeur (résultat central). """
    situations = read_result("situations.csv")
    assert (situations["cout_profondeur"] > 0).all()


# --- routes.csv ---


def test_routes_start_near_the_line():
    """! @brief Au snap, les coureurs sont à moins de 10 yards de la ligne de mêlée. """
    routes = read_result("routes.csv")
    first = routes.sort_values("frameId").groupby(["gameId", "playId", "nflId"]).first()
    assert first["x"].abs().lt(10).all()


def test_routes_contain_both_groups():
    """! @brief Le dessin a des routes avec et sans chip. """
    routes = read_result("routes.csv")
    assert set(routes["chip"]) == {True, False}
