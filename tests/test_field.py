#!/usr/bin/env python3
"""Tests pytest pour src/field.py (terrain + trajets, projet "Le coût du chip")."""

from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import pytest

# Rendre src/ importable sans installation.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from field import (  # noqa: E402
    COULEUR_CHIP,
    COULEUR_SANS_CHIP,
    creer_terrain,
    dessiner_trajets,
    terrain_vide,
)

ROUTES_PATH = os.path.join(REPO_ROOT, "results", "routes.csv")


@pytest.fixture(scope="module")
def routes_df() -> pd.DataFrame:
    """Charge le vrai results/routes.csv."""
    assert os.path.exists(ROUTES_PATH), f"CSV manquant : {ROUTES_PATH}"
    return pd.read_csv(ROUTES_PATH)


def _couleurs_traces(fig: go.Figure) -> list:
    """Retourne la liste des couleurs de ligne des traces mode='lines'."""
    couleurs = []
    for tr in fig.data:
        mode = getattr(tr, "mode", None) or ""
        if "lines" in mode and getattr(tr, "line", None) is not None:
            couleurs.append(tr.line.color)
    return couleurs


# --- Task 3 ------------------------------------------------------------------
def test_terrain_renvoie_figure():
    fig = creer_terrain()
    assert isinstance(fig, go.Figure)
    # alias
    assert isinstance(terrain_vide(), go.Figure)


def test_terrain_ligne_melee_mise_en_evidence():
    fig = creer_terrain()
    # Au moins une shape verticale à x=0 (ligne de mêlée).
    melee = [s for s in fig.layout.shapes if s.x0 == 0 and s.x1 == 0]
    assert melee, "ligne de mêlée (x=0) absente"


# --- Task 4 ------------------------------------------------------------------
def _joueur_avec_les_deux_types(df: pd.DataFrame):
    """Trouve un nflId ayant au moins un trajet chip et un sans chip."""
    chip = df["chip"].astype(str).str.lower().isin(["true", "1"])
    for nfl_id, sub in df.groupby("nflId"):
        masque = chip.loc[sub.index]
        if masque.any() and (~masque).any():
            return nfl_id
    return None


def test_dessiner_trajets_couleurs(routes_df):
    nfl_id = _joueur_avec_les_deux_types(routes_df)
    assert nfl_id is not None, "aucun joueur avec chip ET sans chip dans les données"

    fig = dessiner_trajets(routes_df, nfl_id)
    assert isinstance(fig, go.Figure)

    couleurs = _couleurs_traces(fig)
    assert len(couleurs) > 0, "aucune trace de trajet tracée"
    assert COULEUR_CHIP in couleurs, "aucune trace rouge (avec chip)"
    assert COULEUR_SANS_CHIP in couleurs, "aucune trace bleue (sans chip)"


def test_dessiner_trajets_legende_unique(routes_df):
    """Une seule entrée de légende par catégorie (pas de doublon par play)."""
    nfl_id = _joueur_avec_les_deux_types(routes_df)
    fig = dessiner_trajets(routes_df, nfl_id)

    entrees = {}
    for tr in fig.data:
        if getattr(tr, "showlegend", None) and tr.name:
            entrees[tr.name] = entrees.get(tr.name, 0) + 1

    assert entrees.get("Avec chip", 0) == 1
    assert entrees.get("Sans chip", 0) == 1


def test_dessiner_trajets_nflid_inconnu(routes_df):
    fig = dessiner_trajets(routes_df, 999999999)
    assert isinstance(fig, go.Figure)
    # Aucun trajet tracé.
    assert len(_couleurs_traces(fig)) == 0


# --- Task 5 : robustesse -----------------------------------------------------
def test_robustesse_colonnes_manquantes(routes_df):
    """Un routes_df sans down/yardsToGo/couverture ne doit pas crasher."""
    tronque = routes_df.drop(columns=["down", "yardsToGo", "couverture"])
    nfl_id = _joueur_avec_les_deux_types(routes_df)
    fig = dessiner_trajets(tronque, nfl_id)
    assert isinstance(fig, go.Figure)
    assert len(_couleurs_traces(fig)) > 0


def test_robustesse_profondeur_seule(routes_df):
    """DataFrame réduit (nflId + x seulement, groupé)."""
    reduit = routes_df[["gameId", "playId", "nflId", "frameId", "x"]].copy()
    nfl_id = _joueur_avec_les_deux_types(routes_df)
    fig = dessiner_trajets(reduit, nfl_id)
    assert isinstance(fig, go.Figure)
    # Sans colonne chip, tout est considéré "sans chip" (bleu) -> pas de crash.
    assert len(_couleurs_traces(fig)) > 0


def test_robustesse_chip_en_chaine():
    """chip stocké en chaîne "True"/"False" doit être interprété correctement."""
    df = pd.DataFrame(
        {
            "gameId": [1, 1, 1, 1],
            "playId": [10, 10, 11, 11],
            "nflId": [50001, 50001, 50001, 50001],
            "frameId": [1, 2, 1, 2],
            "x": [0.0, 5.0, 0.0, 6.0],
            "y": [0.0, 1.0, 0.0, -1.0],
            "chip": ["True", "True", "False", "False"],
        }
    )
    fig = dessiner_trajets(df, 50001)
    couleurs = _couleurs_traces(fig)
    assert COULEUR_CHIP in couleurs
    assert COULEUR_SANS_CHIP in couleurs


def test_dataframe_vide_placeholder():
    vide = pd.DataFrame(columns=["gameId", "playId", "nflId", "frameId", "x", "y", "chip"])
    fig = dessiner_trajets(vide, 123)
    assert isinstance(fig, go.Figure)
    textes = [a.text for a in fig.layout.annotations]
    assert any("Aucune donnée" in (t or "") for t in textes)
