#!/usr/bin/env python3
"""Tests du module src/situations.py (Task 6 — coût du chip par situation)."""

from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import pytest

from src.situations import bucket_yards, graphique_situations

# --- Chemins -----------------------------------------------------------------
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
ROUTES_PATH = os.path.join(REPO_ROOT, "results", "routes.csv")


@pytest.fixture(scope="module")
def routes_df() -> pd.DataFrame:
    """Charge le vrai results/routes.csv avec pandas."""
    assert os.path.exists(ROUTES_PATH), f"CSV introuvable : {ROUTES_PATH}"
    return pd.read_csv(ROUTES_PATH)


def test_graphique_renvoie_figure(routes_df: pd.DataFrame) -> None:
    """graphique_situations renvoie une go.Figure sur les vraies données."""
    fig = graphique_situations(routes_df)
    assert isinstance(fig, go.Figure)
    # La figure doit contenir au moins une trace (heatmap) exploitable.
    assert len(fig.data) >= 1


def test_bucketisation_yards() -> None:
    """Vérifie la bucketisation court / moyen / long."""
    assert bucket_yards(2) == "court"
    assert bucket_yards(6) == "moyen"
    assert bucket_yards(10) == "long"
    # Bornes.
    assert bucket_yards(3) == "court"
    assert bucket_yards(4) == "moyen"
    assert bucket_yards(7) == "moyen"
    assert bucket_yards(8) == "long"


def test_robustesse_sans_colonne_couverture(routes_df: pd.DataFrame) -> None:
    """Un routes_df sans la colonne couverture ne doit pas faire crasher."""
    sans_couv = routes_df.drop(columns=["couverture"])
    fig = graphique_situations(sans_couv)
    assert isinstance(fig, go.Figure)


def test_robustesse_chip_en_chaine(routes_df: pd.DataFrame) -> None:
    """chip fourni en chaîne 'True'/'False' doit être accepté."""
    df = routes_df.copy()
    df["chip"] = df["chip"].astype(str)
    fig = graphique_situations(df)
    assert isinstance(fig, go.Figure)


def test_robustesse_donnees_vides() -> None:
    """Un DataFrame vide renvoie une figure placeholder, pas d'exception."""
    vide = pd.DataFrame(columns=["gameId", "playId", "nflId", "x", "chip"])
    fig = graphique_situations(vide)
    assert isinstance(fig, go.Figure)
