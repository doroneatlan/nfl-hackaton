"""!
@file test_figures.py
@brief Tests des figures du README et de l'ordre des situations.
"""

import pandas as pd
import pytest

from src.figures import RESULTS_DIR, plot_cost_vs_gain, plot_routes, plot_situations
from src.situation_stats import DISTANCE_LABELS


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


def test_cost_vs_gain_shows_every_judged_player():
    """! @brief Le nuage contient un point par joueur jugé (rentable, incertain ou pas rentable). """
    summary = read_result("player_summary.csv")
    judged = summary["verdict"].isin(["rentable", "incertain", "pas rentable"]).sum()
    fig = plot_cost_vs_gain(summary)
    points = sum(len(collection.get_offsets()) for collection in fig.axes[0].collections)
    assert points == judged


def test_situations_figure_has_two_bars_per_row():
    """! @brief Une barre "attendue" et une barre "réelle" par situation. """
    situations = read_result("situations.csv")
    fig = plot_situations(situations)
    assert len(fig.axes[0].patches) == 2 * len(situations)


def test_routes_figure_has_one_panel_per_player():
    """! @brief Le dessin des trajets compare deux joueurs côte à côte. """
    fig = plot_routes(read_result("routes.csv"), read_result("player_summary.csv"))
    assert len(fig.axes) == 2


def test_distances_are_in_football_order():
    """! @brief Les distances vont de la plus courte à la plus longue, pas par ordre alphabétique. """
    situations = read_result("situations.csv")
    distances = situations.loc[situations["situation"] == "distance", "valeur"].tolist()
    assert distances == [label for label in DISTANCE_LABELS if label in distances]
